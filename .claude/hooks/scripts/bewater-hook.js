#!/usr/bin/env node
/**
 * BeWater hook: enforce risk-based quality strategy, validation blockers, and traceability.
 * Dependency-free (Node stdlib only).
 *
 * Usage:
 *   node hooks/scripts/bewater-hook.js --mode pre-commit
 *   node hooks/scripts/bewater-hook.js --mode ci
 *   node hooks/scripts/bewater-hook.js --mode ci --check-coverage
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const root = process.cwd();

// ── SSOT: Risk-Level Policy Mapping ──────────────────────────
// 阈值定义的权威来源是 CLAUDE.md "TDD 质量策略" 章节，此处保持同步。
const RISK_POLICY = {
  Critical: { tdd: /必须|must/i,       cov: 80, cr: /必须|must/i },
  High:     { tdd: /必须|must/i,       cov: 70, cr: /必须|must/i },
  Medium:   { tdd: /必须|must/i,       cov: 60, cr: /抽检|必须|must/i },
  Low:      { tdd: /必须|must/i,       cov: 50, cr: /可选|optional|抽检|必须|must/i },
};

// ── Helpers ──────────────────────────────────────────────────

function fail(msg) {
  console.error(`❌ BeWater hook: ${msg}`);
  process.exit(1);
}

function warn(msg) {
  console.warn(`⚠️  BeWater hook: ${msg}`);
}

function info(msg) {
  console.log(`ℹ️  BeWater hook: ${msg}`);
}

function readText(rel) {
  const p = path.join(root, rel);
  if (!fs.existsSync(p)) return null;
  return fs.readFileSync(p, 'utf8');
}

function requireFile(rel, label) {
  const txt = readText(rel);
  if (!txt) fail(`${label} 缺失: ${rel}`);
  return txt;
}

// ── 1. Traceability Check ────────────────────────────────────

const TASKS_FORMAT_VERSION = '1.0';

function checkTasksFormatVersion(featureDir) {
  const tasksPath = `docs/01-features/${featureDir}/tasks.md`;
  const tasks = readText(tasksPath);
  if (!tasks) return; // 缺失由后续检查报错
  const versionMatch = tasks.match(/<!-- format-version:\s*(.+?)\s*-->/);
  if (!versionMatch) {
    warn(`[${featureDir}] tasks.md 缺少 format-version 注释（期望 v${TASKS_FORMAT_VERSION}）`);
  } else if (versionMatch[1] !== TASKS_FORMAT_VERSION) {
    warn(`[${featureDir}] tasks.md format-version=${versionMatch[1]}，当前期望 v${TASKS_FORMAT_VERSION}`);
  }
}

function readStateJson() {
  const statePath = path.join(root, '.bewater/state.json');
  if (!fs.existsSync(statePath)) return null;
  try {
    return JSON.parse(fs.readFileSync(statePath, 'utf8'));
  } catch { return null; }
}

function findFeatureDir(featureNumber) {
  const state = readStateJson();
  if (state) {
    const allFeatures = state.shipped_features || [];
    if (featureNumber) {
      const match = allFeatures.find(k => k.startsWith(featureNumber + '-'));
      if (match) return match;
    }
    if (state.current_feature) {
      return state.current_feature;
    }
  }

  // fallback: 扫描目录取最新的
  const featuresDir = path.join(root, 'docs/01-features');
  if (!fs.existsSync(featuresDir)) return null;

  const dirs = fs.readdirSync(featuresDir)
    .filter(d => fs.statSync(path.join(featuresDir, d)).isDirectory())
    .sort()
    .reverse();

  return dirs[0] || null;
}

function getFeatureState(featureId) {
  const state = readStateJson();
  if (!state) return null;
  const shipped = state.shipped_features || [];
  if (shipped.includes(featureId)) return { state: 'shipped' };
  if (state.current_feature === featureId) return { state: state.current_state };
  return null;
}

function getActiveFeatureDirs() {
  const state = readStateJson();
  if (state && state.current_feature) {
    return [state.current_feature];
  }
  // fallback: 取最新的一个
  const d = findFeatureDir();
  return d ? [d] : [];
}

function checkTraceability() {
  const featureDirs = getActiveFeatureDirs();
  if (featureDirs.length === 0) {
    warn('未找到功能目录，跳过追溯性检查');
    return;
  }

  for (const featureDir of featureDirs) {
    checkTasksFormatVersion(featureDir);
    const featurePath = `docs/01-features/${featureDir}/feature.md`;
    const tasksPath = `docs/01-features/${featureDir}/tasks.md`;

    if (!readText(featurePath)) fail(`${featurePath} 缺失`);

    const tasks = readText(tasksPath);
    if (!tasks) {
      fail(`${tasksPath} 缺失`);
    }

    if (!/验收标准[^]*?- \[ \]/.test(tasks) && !/验收标准[^]*?- \[x\]/i.test(tasks)) {
      fail('tasks.md 缺少验收标准清单');
    }
  }
}

// ── 2. Risk Policy Compliance (document-level) ───────────────

function classifyRisk(raw) {
  // 支持多种格式：emoji、中文、英文、数字
  if (/🔴|critical|严重/i.test(raw)) return 'Critical';
  if (/🟠|high|高/i.test(raw))     return 'High';
  if (/🟡|med|中/i.test(raw))      return 'Medium';
  if (/🟢|low|低/i.test(raw))      return 'Low';
  return null;
}

function parseTasksRiskStrategies(featureDir) {
  if (!featureDir) {
    const dirs = getActiveFeatureDirs();
    if (dirs.length === 0) fail('未找到功能目录');
    featureDir = dirs[0]; // 默认取第一个
  }
  const tasksText = requireFile(`docs/01-features/${featureDir}/tasks.md`, 'tasks');
  const blocks = tasksText.split(/^###\s+Task\s+/m).slice(1);
  return blocks.map((block) => {
    const idMatch = block.match(/^(\d+)/);
    const rawRisk = (block.match(/风险等级[^:]*:\s*(.+)/i) || [])[1] || '';

    // 支持两种格式：
    // 1. 单行格式: - TDD 必须 / 覆盖率 ≥ 60% / CR 抽检
    // 2. 多行格式: TDD: 必须
    const qualityLine = (block.match(/质量策略[^:]*:[^]*?-\s*(.+)/i) || [])[1] || '';
    const tdd = qualityLine ?
      (qualityLine.match(/TDD\s*([^/\n]+)/i) || [])[1] || '' :
      (block.match(/TDD[^:]*:\s*([^\n]+)/i) || [])[1] || '';
    const cov = qualityLine ?
      (qualityLine.match(/覆盖率[^≥>=]*[≥>=]\s*(\d+)%/i) || [])[1] || '' :
      (block.match(/覆盖率[^:]*:\s*[^0-9]*(\d+)%/i) || [])[1] || '';
    const cr = qualityLine ?
      (qualityLine.match(/CR\s*([^/\n]+)/i) || [])[1] || '' :
      (block.match(/Code Review[^:]*:\s*([^\n]+)/i) || [])[1] || '';

    return {
      id: idMatch ? idMatch[1] : '?',
      rawRisk,
      risk: classifyRisk(rawRisk),
      tdd: tdd.trim(),
      cov: Number(cov) || 0,
      cr: cr.trim(),
    };
  });
}

function checkRiskPolicy() {
  const featureDirs = getActiveFeatureDirs();
  if (featureDirs.length === 0) {
    warn('未找到活跃功能目录，跳过风险策略检查');
    return;
  }

  let totalTasks = 0;
  const allErrors = [];

  for (const featureDir of featureDirs) {
    // 只检查非 shipped 的 feature
    const fState = getFeatureState(featureDir);
    if (fState && fState.state === 'shipped') continue;

    const tasks = parseTasksRiskStrategies(featureDir);
    const errors = [];

    for (const t of tasks) {
      if (!t.risk) {
        errors.push(`[${featureDir}] Task ${t.id}: 未标注风险等级`);
        continue;
      }
      const rule = RISK_POLICY[t.risk];
      if (t.cov > 0 && t.cov < rule.cov) {
        errors.push(`[${featureDir}] Task ${t.id}: 覆盖率门槛 ${t.cov}% < 要求 ${rule.cov}% (${t.risk})`);
      }
      if (!rule.tdd.test(t.tdd)) {
        errors.push(`[${featureDir}] Task ${t.id}: TDD 策略不符 "${t.tdd || '未填'}" (${t.risk})`);
      }
      if (!rule.cr.test(t.cr)) {
        errors.push(`[${featureDir}] Task ${t.id}: Code Review 策略不符 "${t.cr || '未填'}" (${t.risk})`);
      }
    }

    totalTasks += tasks.length;
    allErrors.push(...errors);
  }

  if (allErrors.length) fail(allErrors.join('\n'));
  info(`风险策略合规检查: ${totalTasks} 个任务通过 (${featureDirs.length} 个功能)`);
}

// ── 3. Actual Coverage Check ─────────────────────────────────

function detectProjectType() {
  if (fs.existsSync(path.join(root, 'package.json'))) return 'node';
  if (fs.existsSync(path.join(root, 'setup.py')) || fs.existsSync(path.join(root, 'pyproject.toml'))) return 'python';
  return null;
}

function getCoverageResult() {
  const type = detectProjectType();
  if (!type) {
    warn('无法检测项目类型，跳过实际覆盖率检查');
    return null;
  }

  try {
    if (type === 'node') {
      // Try npm run coverage first, then npx jest --coverage
      let output;
      try {
        output = execSync('npm run coverage 2>&1', { cwd: root, encoding: 'utf8', timeout: 120000 });
      } catch (e) {
        // npm run coverage failed, try npx jest
        try {
          output = execSync('npx jest --coverage --coverageReporters=text 2>&1', {
            cwd: root, encoding: 'utf8', timeout: 120000,
          });
        } catch (e2) {
          output = e2.stdout || e2.output || '';
        }
      }
      const match = output.match(/All files[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|\s*([\d.]+)/);
      if (match) return { type: 'node', coverage: parseFloat(match[1]), output };
    } else if (type === 'python') {
      let output;
      try {
        output = execSync('python3 -m pytest --cov --cov-report=term-missing 2>&1', {
          cwd: root, encoding: 'utf8', timeout: 120000,
        });
      } catch (e) {
        output = e.stdout || e.output || '';
      }
      const match = output.match(/TOTAL\s+\d+\s+\d+\s+(\d+)%/);
      if (match) return { type: 'python', coverage: parseInt(match[1]), output };
    }
  } catch (e) {
    warn(`覆盖率检查执行失败: ${e.message}`);
  }
  return null;
}

function checkActualCoverage() {
  const mode = process.argv.includes('--mode')
    ? process.argv[process.argv.indexOf('--mode') + 1]
    : 'pre-commit';

  const shouldCheck = mode === 'ci' || process.argv.includes('--check-coverage');

  if (!shouldCheck) {
    info('跳过实际覆盖率检查（CI 模式或 --check-coverage 启用）');
    return;
  }

  const result = getCoverageResult();
  if (!result) {
    warn('无法获取覆盖率数据');
    return;
  }

  info(`实际覆盖率: ${result.coverage}%`);

  // Collect thresholds from all active non-shipped features
  const featureDirs = getActiveFeatureDirs();
  let maxThreshold = 60;
  for (const featureDir of featureDirs) {
    const fState = getFeatureState(featureDir);
    if (fState && fState.state === 'shipped') continue;
    const tasks = parseTasksRiskStrategies(featureDir);
    const completedTasks = tasks.filter(t => t.cov > 0);
    if (completedTasks.length) {
      maxThreshold = Math.max(maxThreshold, ...completedTasks.map(t => t.cov));
    }
  }

  if (result.coverage < maxThreshold) {
    fail(`实际覆盖率 ${result.coverage}% < 最高要求 ${maxThreshold}%`);
  }

  info(`覆盖率达标: ${result.coverage}% ≥ ${maxThreshold}%`);
}

// ── 4. Validation Blockers ───────────────────────────────────

function checkValidationBlockers() {
  const featureDirs = getActiveFeatureDirs();
  if (featureDirs.length === 0) {
    warn('未找到活跃功能目录，跳过验证阻断检查');
    return;
  }

  for (const featureDir of featureDirs) {
    const fState = getFeatureState(featureDir);
    if (fState && fState.state === 'shipped') continue;

    const report = readText(`docs/01-features/${featureDir}/validation-report.md`);
    if (!report) {
      warn(`[${featureDir}] validation-report.md 缺失，跳过`);
      continue;
    }
    if (/阻断项清单[^]*?(B\d+)/i.test(report) && /🔴|未完成|⏳/i.test(report)) {
      fail(`[${featureDir}] validation-report.md 存在阻断项未清除`);
    }
    if (/发布决策[^]*?(不批准|有条件发布)/i.test(report)) {
      fail(`[${featureDir}] 发布决策未批准或仍有条件未满足`);
    }
  }
}

// ── 5. TDD Execution Check ───────────────────────────
function checkTDDExecution() {
  const featureDirs = getActiveFeatureDirs();
  if (featureDirs.length === 0) {
    warn('未找到活跃功能目录，跳过 TDD 执行检查');
    return;
  }

  let totalChecked = 0;

  for (const featureDir of featureDirs) {
    const fState = getFeatureState(featureDir);
    if (fState && fState.state === 'shipped') continue;

    const tasks = readText(`docs/01-features/${featureDir}/tasks.md`);
    if (!tasks) {
      warn(`[${featureDir}] tasks.md 缺失，跳过 TDD 执行检查`);
      continue;
    }

    // 支持两种格式
    const hasTddOld = /## TDD 执行记录/.test(tasks) || /### Task \d+ - TDD 执行记录/.test(tasks);
    const hasTddNew = /### Task \d+ - TDD 记录/.test(tasks) || /- 测试文件:\s*`[^`]+`\s*\|\s*覆盖率:\s*\d+%/.test(tasks);

    if (!hasTddOld && !hasTddNew) {
      warn(`[${featureDir}] tasks.md 缺少"TDD 执行记录"章节`);
      continue;
    }

    // 解析任务状态
    const tasksParsed = parseTasksRiskStrategies(featureDir);
    const completedTasks = tasksParsed.filter(t => {
      const taskSection = new RegExp(`### Task ${t.id}[^#]*`).exec(tasks);
      return taskSection && /✅|completed/i.test(taskSection[0]);
    });

    if (completedTasks.length === 0) {
      info(`[${featureDir}] 没有已完成的任务，跳过 TDD 执行检查`);
      continue;
    }

    const errors = [];

    for (const task of completedTasks) {
      const tddPattern = new RegExp(`### Task ${task.id} - TDD 执行记录[^#]*(?=###|$)`, 's');
      const tddSection = tddPattern.exec(tasks);

      if (!tddSection) {
        errors.push(`[${featureDir}] Task ${task.id}: 缺少 TDD 执行记录`);
        continue;
      }

      const section = tddSection[0];

      // 检查 RED 阶段
      if (!/- \[x\] RED/i.test(section)) {
        errors.push(`[${featureDir}] Task ${task.id}: TDD RED 阶段未完成（测试未勾选）`);
      }

      // 检查 GREEN 阶段
      if (!/- \[x\] GREEN/i.test(section)) {
        errors.push(`[${featureDir}] Task ${task.id}: TDD GREEN 阶段未完成（实现未勾选）`);
      }

      // 检查测试文件路径
      const testFileMatch = section.match(/测试文件:\s*`([^`]+)`/);
      if (!testFileMatch || !testFileMatch[1].trim()) {
        errors.push(`[${featureDir}] Task ${task.id}: 缺少测试文件路径`);
      }

      // 检查实现文件路径
      const implFileMatch = section.match(/实现文件:\s*`([^`]+)`/);
      if (!implFileMatch || !implFileMatch[1].trim()) {
        errors.push(`[${featureDir}] Task ${task.id}: 缺少实现文件路径`);
      }

      // 检查文件创建时间顺序（宽松模式）
      const testTimeMatch = section.match(/测试文件[^]*?创建时间:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})/);
      const implTimeMatch = section.match(/实现文件[^]*?创建时间:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})/);

      if (testTimeMatch && implTimeMatch) {
        const testTime = new Date(testTimeMatch[1]);
        const implTime = new Date(implTimeMatch[1]);
        if (!isNaN(testTime.getTime()) && !isNaN(implTime.getTime()) && testTime >= implTime) {
          warn(`[${featureDir}] Task ${task.id}: 测试文件创建时间晚于或等于实现文件（非阻断）`);
        }
      }
    }

    if (errors.length) {
      fail(`TDD 执行检查失败:\n${errors.map(e => `  - ${e}`).join('\n')}`);
    }

    totalChecked += completedTasks.length;
  }

  info(`TDD 执行检查: ${totalChecked} 个任务通过`);
}

// ── 6. Architecture Consistency Check ────────────────────────
// 简化为架构文档存在性检查。完整的架构-代码比对需由 Architect Agent 在运行时执行。
function checkArchitectureConsistency() {
  const archPath = 'docs/00-project/architecture.md';
  const arch = readText(archPath);

  if (!arch) {
    warn('architecture.md 缺失，跳过架构一致性检查');
    return;
  }

  // 检查架构文档是否包含占位符（未填写）
  const placeholderCount = (arch.match(/\[.*?\]/g) || []).length;
  if (placeholderCount > 10) {
    warn(`architecture.md 包含 ${placeholderCount} 个占位符，可能尚未完善`);
  }

  info('架构文档存在性检查通过');
}

// ── 7. Agent Tool Compliance Check ───────────────────────────
// Validates that agent frontmatter tools/disallowedTools are consistent
// and follow the structured schema (inspired by Claude Code BaseAgentDefinition).

const VALID_TOOLS = [
  'Bash', 'Read', 'Write', 'Edit', 'Glob', 'Grep', 'Agent', 'NotebookEdit',
  'WebFetch', 'WebSearch',
];

function parseAgentFrontmatter(relPath) {
  const content = readText(relPath);
  if (!content) return null;

  const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
  if (!fmMatch) return null;

  const fm = fmMatch[1];
  const agent = {};

  // Simple YAML-like parsing for our flat + list schema
  const nameMatch = fm.match(/^name:\s*(.+)$/m);
  agent.name = nameMatch ? nameMatch[1].trim() : null;

  const phaseMatch = fm.match(/^phase:\s*(.+)$/m);
  agent.phase = phaseMatch ? phaseMatch[1].trim() : null;

  // Parse tools list
  const toolsSection = fm.match(/^tools:\s*\n((?:\s+- .+\n?)*)/m);
  if (toolsSection) {
    agent.tools = toolsSection[1]
      .split('\n')
      .map(l => l.replace(/^\s+-\s+/, '').trim())
      .filter(Boolean);
  }

  // Parse disallowedTools list
  const disallowedSection = fm.match(/^disallowedTools:\s*\n((?:\s+- .+\n?)*)/m);
  if (disallowedSection) {
    agent.disallowedTools = disallowedSection[1]
      .split('\n')
      .map(l => l.replace(/^\s+-\s+/, '').trim())
      .filter(Boolean);
  } else if (disallowedSection === null) {
    // Try inline array format
    const disallowedInline = fm.match(/^disallowedTools:\s*\[(.+)\]/m);
    if (disallowedInline) {
      agent.disallowedTools = disallowedInline[1].split(',').map(s => s.trim());
    }
  }

  // Empty disallowedTools list
  const disallowedEmpty = fm.match(/^disallowedTools:\s*\[\]/m);
  if (disallowedEmpty) {
    agent.disallowedTools = [];
  }

  return agent;
}

function checkAgentToolCompliance() {
  const agentsDir = path.join(root, '.claude', 'agents');
  if (!fs.existsSync(agentsDir)) {
    info('agents/ 目录不存在，跳过 Agent 工具合规检查');
    return;
  }

  const agentFiles = fs.readdirSync(agentsDir)
    .filter(f => f.endsWith('.md'));

  if (agentFiles.length === 0) {
    info('agents/ 目录为空，跳过 Agent 工具合规检查');
    return;
  }

  const errors = [];

  for (const file of agentFiles) {
    const agent = parseAgentFrontmatter(`.claude/agents/${file}`);
    if (!agent) {
      warn(`agents/${file}: 无法解析 frontmatter`);
      continue;
    }

    if (!agent.name) {
      errors.push(`agents/${file}: 缺少 name 字段`);
      continue;
    }

    // Validate tools list
    if (agent.tools) {
      for (const tool of agent.tools) {
        if (!VALID_TOOLS.includes(tool)) {
          errors.push(`agents/${file} (${agent.name}): 未知工具 "${tool}"`);
        }
      }
    }

    // Validate disallowedTools list
    if (agent.disallowedTools) {
      for (const tool of agent.disallowedTools) {
        if (!VALID_TOOLS.includes(tool)) {
          errors.push(`agents/${file} (${agent.name}): 未知禁用工具 "${tool}"`);
        }
      }
    }

    // Check for overlap (tool in both lists)
    if (agent.tools && agent.disallowedTools) {
      const overlap = agent.tools.filter(t => agent.disallowedTools.includes(t));
      if (overlap.length > 0) {
        errors.push(`agents/${file} (${agent.name}): 工具同时出现在 tools 和 disallowedTools: ${overlap.join(', ')}`);
      }
    }

    // Validate mandatory fields for schema v2.0.0
    if (!agent.phase) {
      errors.push(`agents/${file} (${agent.name}): 缺少 phase 字段`);
    }
    if (!agent.tools || agent.tools.length === 0) {
      errors.push(`agents/${file} (${agent.name}): 缺少 tools 字段（至少需要一个工具）`);
    }
  }

  if (errors.length) {
    fail(`Agent 工具合规检查失败:\n${errors.map(e => `  - ${e}`).join('\n')}`);
  }

  info(`Agent 工具合规检查: ${agentFiles.length} 个 Agent 通过`);
}

// ── Main ─────────────────────────────────────────────────────

function main() {
  const mode = process.argv.includes('--mode')
    ? process.argv[process.argv.indexOf('--mode') + 1]
    : 'pre-commit';

  info(`运行模式: ${mode}`);

  checkTraceability();
  checkRiskPolicy();
  checkActualCoverage();
  checkValidationBlockers();
  checkTDDExecution();
  checkArchitectureConsistency();
  checkAgentToolCompliance();

  console.log(`✅ BeWater hook (${mode}) 通过`);
}

main();
