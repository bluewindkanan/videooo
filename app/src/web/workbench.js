/* Videooo Workbench — SPA with hash routing */
(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // API helper
  // ---------------------------------------------------------------------------
  async function api(path, init) {
    var res = await fetch(path, init);
    var text = await res.text();
    var data;
    try { data = JSON.parse(text); } catch (e) { data = { raw: text }; }
    if (!res.ok) {
      throw new Error(res.status + " " + res.statusText + ": " + text);
    }
    return data;
  }

  // ---------------------------------------------------------------------------
  // Routing
  // ---------------------------------------------------------------------------
  var pages = {
    list: document.getElementById("page-list"),
    detail: document.getElementById("page-detail"),
    new: document.getElementById("page-new"),
  };

  function showPage(name) {
    Object.keys(pages).forEach(function (k) {
      pages[k].classList.toggle("active", k === name);
    });
  }

  var _refreshTimer = null;

  function stopAutoRefresh() {
    if (_refreshTimer) {
      clearInterval(_refreshTimer);
      _refreshTimer = null;
    }
  }

  function route() {
    stopAutoRefresh();
    var hash = location.hash || "#/";
    if (hash === "#/" || hash === "#") {
      showPage("list");
      loadTaskList();
    } else if (hash === "#/new") {
      showPage("new");
    } else {
      var m = hash.match(/^#\/task\/([a-f0-9]+)$/);
      if (m) {
        showPage("detail");
        loadTaskDetail(m[1]);
      } else {
        showPage("list");
        loadTaskList();
      }
    }
  }

  window.addEventListener("hashchange", route);

  // ---------------------------------------------------------------------------
  // Task List Page
  // ---------------------------------------------------------------------------
  function loadTaskList() {
    var container = document.getElementById("task-list");
    container.innerHTML = '<div class="empty-state">加载中...</div>';

    api("/api/video-tasks")
      .then(function (data) {
        if (!data.tasks || data.tasks.length === 0) {
          container.innerHTML =
            '<div class="empty-state">' +
            '<p>暂无任务</p>' +
            '<a href="#/new" class="btn btn-primary">创建第一个任务</a>' +
            "</div>";
          return;
        }
        container.innerHTML = data.tasks
          .map(function (t) {
            return (
              '<div class="card card-clickable" data-task-id="' +
              t.id +
              '">' +
              '<div class="card-row">' +
              '<span class="card-id">' +
              escHtml(t.id.slice(0, 8)) +
              "</span>" +
              '<span class="badge badge-' +
              escHtml(t.status) +
              '">' +
              escHtml(t.status) +
              "</span>" +
              '<span class="card-summary">' +
              escHtml(t.input_text_summary) +
              "</span>" +
              '<span class="card-date">' +
              escHtml(formatDate(t.created_at)) +
              "</span>" +
              "</div>" +
              "</div>"
            );
          })
          .join("");

        container.querySelectorAll(".card-clickable").forEach(function (el) {
          el.addEventListener("click", function () {
            location.hash = "#/task/" + el.getAttribute("data-task-id");
          });
        });
      })
      .catch(function (err) {
        container.innerHTML =
          '<div class="empty-state" style="color:var(--c-failed);">' +
          escHtml(err.message) +
          "</div>";
      });
  }

  // ---------------------------------------------------------------------------
  // Task Detail Page
  // ---------------------------------------------------------------------------
  function loadTaskDetail(taskId) {
    var container = document.getElementById("detail-content");
    document.getElementById("detail-title").textContent = "任务 " + taskId.slice(0, 8);
    container.innerHTML = '<div class="empty-state">加载中...</div>';

    Promise.all([
      api("/api/video-tasks/" + taskId),
      api("/api/video-tasks/" + taskId + "/artifacts"),
    ])
      .then(function (results) {
        var detail = results[0];
        var artData = results[1];
        renderTaskDetail(container, detail, artData);

        // Auto-refresh every 5s if any step is running
        var hasRunning = detail.steps.some(function (s) {
          return s.status === "running" || s.status === "pending";
        });
        if (hasRunning) {
          _refreshTimer = setInterval(function () {
            Promise.all([
              api("/api/video-tasks/" + taskId),
              api("/api/video-tasks/" + taskId + "/artifacts"),
            ]).then(function (r) {
              renderTaskDetail(container, r[0], r[1]);
            });
          }, 5000);
        }
      })
      .catch(function (err) {
        container.innerHTML =
          '<div class="empty-state" style="color:var(--c-failed);">' +
          escHtml(err.message) +
          "</div>";
      });
  }

  function renderTaskDetail(container, detail, artData) {
    var task = detail.task;
    var steps = detail.steps;
    var artifacts = artData.artifacts;

    var html = "";

    // Task info card
    html += '<div class="card">';
    html += '<div class="info-grid">';
    html += '<span class="label">状态</span><span><span class="badge badge-' + escHtml(task.status) + '">' + escHtml(task.status) + "</span></span>";
    html += '<span class="label">输入类型</span><span>' + escHtml(task.input_kind) + "</span>";
    html += '<span class="label">输入内容</span><span>' + escHtml(task.input_text) + "</span>";
    html += '<span class="label">素材链接</span><span>' + (task.source_links.length > 0 ? task.source_links.map(escHtml).join("<br />") : "(无)") + "</span>";
    html += '<span class="label">创建时间</span><span>' + escHtml(formatDate(task.created_at)) + "</span>";
    html += "</div></div>";

    // Steps row
    html += '<div class="steps-row">';
    steps.forEach(function (s) {
      html += '<div class="step-card">';
      html += '<div class="step-key">' + escHtml(s.step_key) + "</div>";
      html += '<span class="badge badge-' + escHtml(s.status) + '">' + escHtml(s.status) + "</span>";
      if (s.error_message) {
        html += '<div class="step-error">' + escHtml(s.error_message) + "</div>";
      }
      if (s.status === "failed") {
        html += '<button class="btn btn-danger retry-btn" data-step="' + escHtml(s.step_key) + '" style="margin-top:8px;font-size:0.75rem;padding:4px 8px;">重试</button>';
      }
      html += "</div>";
    });
    html += "</div>";

    // Product display: load artifact content
    html += renderProductSections(task.id, artifacts);

    // Material status panel
    html += renderMaterialPanel(task, artifacts);

    container.innerHTML = html;

    // Bind retry buttons
    container.querySelectorAll(".retry-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var stepKey = btn.getAttribute("data-step");
        btn.disabled = true;
        btn.textContent = "重试中...";
        api("/api/video-tasks/" + task.id + "/retry", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ step_key: stepKey }),
        })
          .then(function () {
            loadTaskDetail(task.id);
          })
          .catch(function (err) {
            btn.textContent = "重试失败";
            btn.disabled = false;
            console.error(err);
          });
      });
    });

    // Bind artifact content loaders
    container.querySelectorAll(".artifact-loader").forEach(function (el) {
      var artId = el.getAttribute("data-artifact-id");
      var taskId = el.getAttribute("data-task-id");
      var targetId = el.getAttribute("data-target");
      api("/api/video-tasks/" + taskId + "/artifacts/" + artId + "/content")
        .then(function (data) {
          if (el.getAttribute("data-step") === "material_fetch") {
            document.getElementById(targetId).innerHTML = renderMaterialStatusContent(data.content);
          } else {
            renderArtifactContent(targetId, data.content, el.getAttribute("data-step"));
          }
        })
        .catch(function (err) {
          document.getElementById(targetId).innerHTML =
            '<div style="color:var(--c-failed);font-size:0.8rem;">' + escHtml(err.message) + "</div>";
        });
    });

    // Bind material upload button
    var uploadBtn = document.getElementById("material-upload-btn");
    if (uploadBtn) {
      uploadBtn.addEventListener("click", function () {
        var input = document.getElementById("material-upload-input");
        var statusEl = document.getElementById("material-upload-status");
        if (!input || !input.files || input.files.length === 0) {
          statusEl.textContent = "请选择文件";
          return;
        }
        var file = input.files[0];
        var fd = new FormData();
        fd.append("file", file);
        uploadBtn.disabled = true;
        statusEl.textContent = "上传中...";
        fetch("/api/video-tasks/" + task.id + "/materials", { method: "POST", body: fd })
          .then(function (r) {
            if (!r.ok) throw new Error("上传失败: " + r.status);
            return r.json();
          })
          .then(function () {
            statusEl.textContent = "上传成功，刷新中...";
            loadTaskDetail(task.id);
          })
          .catch(function (err) {
            statusEl.textContent = escHtml(err.message);
            uploadBtn.disabled = false;
          });
      });
    }
  }

  var FAILURE_LABELS = {
    unreachable: "无法访问",
    timeout: "下载超时",
    unsupported_format: "格式不支持",
    size_exceeded: "文件过大",
    platform_restriction: "平台限制",
  };

  function renderMaterialPanel(task, artifacts) {
    var materialArts = (artifacts || []).filter(function (a) {
      return a.artifact_type === "material_status";
    });
    if (materialArts.length === 0 && task.status !== "waiting_for_material") return "";

    var html = '<div class="card" style="margin-top:16px;">';
    html += '<h3 style="margin:0 0 12px 0;font-size:1rem;">素材状态</h3>';

    if (materialArts.length > 0) {
      html += '<div id="material-status-content" class="artifact-loader" data-artifact-id="' + escHtml(materialArts[0].id) + '" data-task-id="' + escHtml(task.id) + '" data-target="material-status-target" data-step="material_fetch">';
      html += '<div id="material-status-target" style="color:#888;font-size:0.85rem;">加载中...</div>';
      html += '</div>';
    }

    if (task.status === "waiting_for_material") {
      html += '<div style="margin-top:12px;padding:12px;border:1px dashed var(--c-border);border-radius:6px;">';
      html += '<p style="margin:0 0 8px 0;font-size:0.85rem;color:var(--c-failed);">素材下载全部失败，请上传替代素材：</p>';
      html += '<input type="file" id="material-upload-input" accept=".mp4,.mov,.avi" style="font-size:0.85rem;" />';
      html += '<button id="material-upload-btn" class="btn btn-primary" style="margin-left:8px;font-size:0.8rem;padding:4px 12px;">上传</button>';
      html += '<span id="material-upload-status" style="margin-left:8px;font-size:0.8rem;color:#888;"></span>';
      html += '</div>';
    }

    html += '</div>';
    return html;
  }

  function renderMaterialStatusContent(content) {
    if (!Array.isArray(content)) return '<div style="font-size:0.85rem;">无素材状态数据</div>';
    var html = '<table style="width:100%;font-size:0.85rem;border-collapse:collapse;">';
    html += '<tr style="border-bottom:1px solid var(--c-border);"><th style="text-align:left;padding:4px;">链接</th><th style="text-align:left;padding:4px;">状态</th><th style="text-align:left;padding:4px;">原因</th></tr>';
    content.forEach(function (item) {
      var statusBadge = item.status === "success"
        ? '<span style="color:var(--c-completed);">已下载</span>'
        : '<span style="color:var(--c-failed);">失败</span>';
      var reason = item.failure_category ? (FAILURE_LABELS[item.failure_category] || escHtml(item.failure_category)) : "-";
      html += '<tr style="border-bottom:1px solid var(--c-border);">';
      html += '<td style="padding:4px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escHtml(item.url) + '">' + escHtml(item.url) + '</td>';
      html += '<td style="padding:4px;">' + statusBadge + '</td>';
      html += '<td style="padding:4px;">' + reason + '</td>';
      html += '</tr>';
    });
    html += '</table>';
    return html;
  }

  function renderProductSections(taskId, artifacts) {
    var html = "";

    // Group artifacts by step_key
    var byStep = {};
    artifacts.forEach(function (a) {
      if (!byStep[a.step_key]) byStep[a.step_key] = [];
      byStep[a.step_key].push(a);
    });

    // Script section
    var scriptArts = (byStep["script_generation"] || []).filter(function (a) {
      return a.artifact_type === "parsed_json";
    });
    if (scriptArts.length > 0) {
      var targetId = "script-content";
      html += '<h3 class="section-title">脚本产出</h3>';
      html += '<div class="card"><div id="' + targetId + '">加载中...</div></div>';
      html += '<div class="artifact-loader" data-artifact-id="' + scriptArts[0].id + '" data-task-id="' + taskId + '" data-step="script_generation" data-target="' + targetId + '" style="display:none;"></div>';
    }

    // Storyboard section
    var sbArts = (byStep["storyboard"] || []).filter(function (a) {
      return a.artifact_type === "parsed_json";
    });
    if (sbArts.length > 0) {
      var targetId2 = "storyboard-content";
      html += '<h3 class="section-title">分镜表</h3>';
      html += '<div class="card"><div id="' + targetId2 + '">加载中...</div></div>';
      html += '<div class="artifact-loader" data-artifact-id="' + sbArts[0].id + '" data-task-id="' + taskId + '" data-step="storyboard" data-target="' + targetId2 + '" style="display:none;"></div>';
    }

    // Review section
    var revArts = (byStep["review_script"] || []).filter(function (a) {
      return a.artifact_type === "parsed_json";
    });
    if (revArts.length > 0) {
      var targetId3 = "review-content";
      html += '<h3 class="section-title">审核结果</h3>';
      html += '<div id="' + targetId3 + '">加载中...</div>';
      html += '<div class="artifact-loader" data-artifact-id="' + revArts[0].id + '" data-task-id="' + taskId + '" data-step="review_script" data-target="' + targetId3 + '" style="display:none;"></div>';
    }

    // Final video section
    var videoArts = (artifacts || []).filter(function (a) {
      return a.artifact_type === "final_video";
    });
    if (videoArts.length > 0) {
      var videoArtifactId = videoArts[videoArts.length - 1].id;
      var fileUrl = "/api/video-tasks/" + taskId + "/artifacts/" + videoArtifactId + "/file";
      html += '<h3 class="section-title">视频初稿</h3>';
      html += '<div class="card">';
      html += '<video class="video-player" controls preload="metadata">';
      html += '<source src="' + escHtml(fileUrl) + '" type="video/mp4" />';
      html += '您的浏览器不支持视频播放';
      html += '</video>';
      html += '<div class="video-actions">';
      html += '<a href="' + escHtml(fileUrl) + '" download class="btn btn-primary">下载视频</a>';
      html += '</div>';
      html += '</div>';
    }

    // Audio section (voiceover)
    var audioArts = (artifacts || []).filter(function (a) {
      return a.artifact_type === "audio" && a.step_key === "voiceover";
    });
    if (audioArts.length > 0) {
      var audioArtifactId = audioArts[audioArts.length - 1].id;
      var audioUrl = "/api/video-tasks/" + taskId + "/artifacts/" + audioArtifactId + "/file";
      html += '<h3 class="section-title">配音音频</h3>';
      html += '<div class="card">';
      html += '<audio class="audio-player" controls preload="metadata">';
      html += '<source src="' + escHtml(audioUrl) + '" type="audio/mpeg" />';
      html += '您的浏览器不支持音频播放';
      html += '</audio>';
      html += '</div>';
    }

    // Subtitle section
    var srtArts = (artifacts || []).filter(function (a) {
      return a.artifact_type === "subtitle";
    });
    if (srtArts.length > 0) {
      var srtTargetId = "subtitle-content";
      html += '<h3 class="section-title">字幕文件</h3>';
      html += '<div class="card"><div id="' + srtTargetId + '">加载中...</div></div>';
      html += '<div class="artifact-loader" data-artifact-id="' + srtArts[0].id + '" data-task-id="' + taskId + '" data-step="subtitle" data-target="' + srtTargetId + '" style="display:none;"></div>';
    }

    return html;
  }

  function renderArtifactContent(targetId, content, stepKey) {
    var el = document.getElementById(targetId);
    if (!el) return;

    if (stepKey === "script_generation") {
      el.innerHTML =
        '<div class="script-block">' +
        '<div class="hook">' + escHtml(content.hook || "") + "</div>" +
        '<div class="body-text">' + escHtml(content.body || "") + "</div>" +
        '<div class="cta">' + escHtml(content.call_to_action || "") + "</div>" +
        '<div style="margin-top:8px;font-size:0.75rem;color:var(--c-muted);">' +
        "预估时长: " + (content.estimated_duration_seconds || "?") + "秒" +
        "</div>" +
        "</div>";
    } else if (stepKey === "storyboard") {
      var shots = Array.isArray(content) ? content : (content.shots || content.scenes || []);
      if (!Array.isArray(shots) || shots.length === 0) {
        el.innerHTML = '<div class="empty-state">暂无分镜数据</div>';
        return;
      }
      var rows = shots
        .map(function (s, i) {
          return (
            "<tr>" +
            "<td>" + (i + 1) + "</td>" +
            "<td>" + escHtml(s.voiceover_text || "") + "</td>" +
            "<td>" + escHtml(s.visual_intent || "") + "</td>" +
            "<td>" + escHtml((s.expected_keywords || s.keywords || []).join(", ")) + "</td>" +
            "<td>" + escHtml((s.estimated_start_seconds != null ? s.estimated_start_seconds + "s" : "") + "–" + (s.estimated_end_seconds != null ? s.estimated_end_seconds + "s" : "")) + "</td>" +
            "</tr>"
          );
        })
        .join("");
      el.innerHTML =
        '<table class="storyboard-table">' +
        "<thead><tr><th>#</th><th>旁白</th><th>画面意图</th><th>关键词</th><th>时间范围</th></tr></thead>" +
        "<tbody>" + rows + "</tbody></table>";
    } else if (stepKey === "review_script") {
      var issues = Array.isArray(content) ? content : (content.issues || []);
      if (issues.length === 0) {
        el.innerHTML =
          '<div class="card"><div class="empty-state">审核通过，无问题</div></div>';
        return;
      }
      el.innerHTML = issues
        .map(function (iss) {
          return (
            '<div class="issue-card">' +
            '<div class="issue-header">' +
            '<span class="badge badge-' + escHtml(iss.severity || "info") + '">' + escHtml(iss.severity || "info") + "</span>" +
            '<span class="issue-location">' + escHtml(iss.location_ref || "") + "</span>" +
            "</div>" +
            '<div class="issue-message">' + escHtml(iss.message || "") + "</div>" +
            (iss.suggested_fix
              ? '<div class="issue-fix">建议: ' + escHtml(iss.suggested_fix) + "</div>"
              : "") +
            "</div>"
          );
        })
        .join("");
    } else if (stepKey === "subtitle") {
      // content is {"content": "1\n00:00:00,000 --> ..."}
      var srtText = content.content || content;
      if (typeof srtText === "string") {
        el.innerHTML = '<pre style="white-space:pre-wrap;font-size:0.8rem;max-height:300px;overflow-y:auto;">' + escHtml(srtText) + '</pre>';
      } else {
        el.innerHTML = '<pre>' + escHtml(JSON.stringify(content, null, 2)) + '</pre>';
      }
    } else {
      el.innerHTML = "<pre>" + escHtml(JSON.stringify(content, null, 2)) + "</pre>";
    }
  }

  // ---------------------------------------------------------------------------
  // Create Task Page
  // ---------------------------------------------------------------------------
  var submitBtn = document.getElementById("new-submit");
  var errorSpan = document.getElementById("new-error");

  submitBtn.addEventListener("click", function () {
    var input_kind = document.getElementById("new-input-kind").value;
    var input_text = document.getElementById("new-input-text").value || "";
    var source_links = (document.getElementById("new-source-links").value || "")
      .split("\n")
      .map(function (s) { return s.trim(); })
      .filter(Boolean);

    errorSpan.textContent = "";
    submitBtn.disabled = true;
    submitBtn.textContent = "提交中...";

    api("/api/video-tasks", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ input_kind: input_kind, input_text: input_text, source_links: source_links }),
    })
      .then(function (data) {
        location.hash = "#/task/" + data.task_id;
      })
      .catch(function (err) {
        errorSpan.textContent = err.message;
        submitBtn.disabled = false;
        submitBtn.textContent = "提交";
      });
  });

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------
  function escHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
  }

  function formatDate(isoStr) {
    if (!isoStr) return "";
    try {
      var d = new Date(isoStr);
      return (
        d.getFullYear() +
        "-" +
        pad(d.getMonth() + 1) +
        "-" +
        pad(d.getDate()) +
        " " +
        pad(d.getHours()) +
        ":" +
        pad(d.getMinutes())
      );
    } catch (e) {
      return isoStr;
    }
  }

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  route();
})();
