(function () {
    "use strict";

    function closeSideFrame() {
        try {
            window.top.CMS.API.Sideframe.close();
        } catch (err) {}
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('form.js-close-sideframe').forEach(el => {
            el.addEventListener("submit", (ev) => {
                ev.preventDefault();
                ev.target.action = ev.target.action;  // save action url
                closeSideFrame();
                const form = window.top.document.body.appendChild(ev.target);  // move to top window
                form.style.display = 'none';
                form.submit();  // submit form
            });
        });
    });
})();
