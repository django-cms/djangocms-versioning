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
                closeSideFrame();
                const form = window.top.document.body.appendChild(ev.target);
                form.style.display = 'none';
                form.submit();
            });
        });
    });
})();
