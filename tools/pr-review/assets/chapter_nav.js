// In-chapter change navigation, driven by the review shell via postMessage.
(function () {
  var SEL = ".diff-ins, .diff-del, .diff-ins-block, .diff-del-block";
  var current = -1;

  function visibleMarks() {
    return Array.prototype.filter.call(document.querySelectorAll(SEL), function (el) {
      return el.offsetParent !== null || el.getClientRects().length > 0;
    });
  }

  // One entry per hunk (a hunk may consist of a deletion and an insertion).
  function hunks() {
    var seen = Object.create(null);
    var out = [];
    visibleMarks().forEach(function (el) {
      var id = el.getAttribute("data-hunk") || "";
      if (id && seen[id]) return;
      if (id) seen[id] = true;
      out.push(el);
    });
    return out;
  }

  function report() {
    parent.postMessage(
      { type: "diff:ready", total: hunks().length, index: current },
      "*"
    );
  }

  function go(target) {
    var list = hunks();
    if (!list.length) return;
    if (target < 0) target = list.length - 1;
    if (target >= list.length) target = 0;
    current = target;
    var el = list[current];
    document.querySelectorAll(".diff-current").forEach(function (n) {
      n.classList.remove("diff-current");
    });
    var group = el.getAttribute("data-hunk");
    (group
      ? document.querySelectorAll('[data-hunk="' + group + '"]')
      : [el]
    ).forEach(function (n) {
      n.classList.add("diff-current");
    });
    // explicit scroll: smooth scrollIntoView is unreliable inside an unfocused iframe
    var top = window.scrollY + el.getBoundingClientRect().top - window.innerHeight * 0.3;
    var near = Math.abs(top - window.scrollY) < 1500;
    window.scrollTo({ top: Math.max(top, 0), behavior: near ? "smooth" : "auto" });
    parent.postMessage(
      { type: "diff:position", total: list.length, index: current },
      "*"
    );
  }

  window.addEventListener("message", function (e) {
    var msg = e.data || {};
    if (msg.type === "diff:next") go(current + 1);
    else if (msg.type === "diff:prev") go(current - 1);
    else if (msg.type === "diff:first") go(0);
    else if (msg.type === "diff:deletions") {
      document.body.classList.toggle("hide-deletions", !msg.show);
      current = -1;
      report();
    } else if (msg.type === "diff:query") report();
  });

  // keep keyboard shortcuts working while the iframe has focus
  document.addEventListener("keydown", function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;
    if (e.key === "n" || e.key === "j") { go(current + 1); e.preventDefault(); }
    else if (e.key === "p" || e.key === "k") { go(current - 1); e.preventDefault(); }
    else parent.postMessage({ type: "diff:key", key: e.key }, "*");
  });

  if (document.readyState === "complete") report();
  else window.addEventListener("load", report);
})();
