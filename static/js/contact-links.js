(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    document.querySelectorAll(".js-contact-link").forEach(function (el) {
      var user = el.getAttribute("data-user");
      var domain = el.getAttribute("data-domain");
      if (!user || !domain) return;

      var address = user + "@" + domain;
      var subject = el.getAttribute("data-subject");
      el.setAttribute("href", "mailto:" + address + (subject ? "?subject=" + subject : ""));

      if (el.getAttribute("data-show-address") === "true") {
        el.textContent = address;
      }
    });
  });
})();
