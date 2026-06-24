/*
 * djangocms-versioning admin behaviours.
 *
 * Single, dependency-free entry point for all versioning admin-side JavaScript.
 * It wires up, defensively (a missing control is simply a no-op):
 *
 *   - object-tools versioning buttons (Publish / New Draft) which POST via a
 *     generated form;
 *   - "close sideframe" links (e.g. the Preview link) and confirmation forms;
 *   - the state-indicator pagetree dropdown menu and its AJAX actions;
 *   - version-compare checkbox selection on the version changelist.
 *
 * The actual sideframe close uses the CMS public JS API
 * (window.top.CMS.API.Sideframe.close()); everything else is plain DOM.
 */
(function () {
    'use strict';

    // -- Shared helpers ------------------------------------------------------

    function closeSideFrame() {
        try {
            window.top.CMS.API.Sideframe.close();
        } catch {}
    }

    function showLoader() {
        try {
            window.top.CMS.API.Toolbar.showLoader();
        } catch {}
    }

    function hideLoader() {
        try {
            window.top.CMS.API.Toolbar.hideLoader();
        } catch {}
    }

    function getCsrfToken() {
        try {
            if (window.CMS && window.CMS.config && window.CMS.config.csrf) {
                return window.CMS.config.csrf;
            }
        } catch {}

        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');

        if (input && input.value) {
            return input.value;
        }

        const cookie = document.cookie.match(/csrftoken=([^;]*);?/);

        if (cookie && cookie.length > 1) {
            return cookie[1];
        }

        return null;
    }

    // Build a hidden POST form for `url` and submit it. When `topWindow` is true
    // the form is created in and submitted from the top window, which is needed
    // to break out of the CMS sideframe iframe.
    function postViaForm(url, csrfToken, topWindow) {
        const doc = topWindow ? window.top.document : document;
        const form = doc.createElement('form');
        const input = doc.createElement('input');

        form.method = 'post';
        form.action = url;
        form.style.display = 'none';
        input.type = 'hidden';
        input.name = 'csrfmiddlewaretoken';
        input.value = csrfToken || '';
        form.appendChild(input);
        doc.body.appendChild(form);
        form.submit();
    }

    function showError(message) {
        const messages = document.querySelector('.messagelist');
        const breadcrumbs = document.querySelector('.breadcrumbs');
        let error = '';

        try {
            error = window.top.CMS.config.lang.error || '';
        } catch {}

        const html =
            '<ul class="messagelist"><li class="error"><strong>' +
            error + '</strong> ' + message + '</li></ul>';

        if (messages) {
            messages.outerHTML = html;
            return;
        }

        if (breadcrumbs) {
            breadcrumbs.insertAdjacentHTML('afterend', html);
        }
    }

    function reloadAfterAction() {
        if (window.self === window.top) {
            window.location.reload();
            return;
        }

        window.top.CMS.API.Helpers.reloadBrowser('REFRESH_PAGE');
    }

    // -- Object-tools versioning buttons -------------------------------------

    function initObjectToolButtons() {
        document.querySelectorAll('.cms-form-post-method').forEach(function (el) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                postViaForm(el.href, getCsrfToken(), false);
            });
        });
    }

    // -- Close-sideframe links and confirmation forms ------------------------

    function initCloseSideframe() {
        // Links (e.g. the Preview link) just close the sideframe; the actual
        // navigation is handled by their target="_parent" attribute.
        document.querySelectorAll('a.js-close-sideframe').forEach(function (el) {
            el.addEventListener('click', closeSideFrame);
        });

        // Confirmation forms close the sideframe, then submit from the top
        // window so the response is not trapped inside the iframe.
        document.querySelectorAll('form.js-close-sideframe').forEach(function (el) {
            el.addEventListener('submit', function (ev) {
                ev.preventDefault();
                // Freeze the action to an absolute URL before moving the form to
                // the top window (a relative action would resolve differently).
                ev.target.action = ev.target.action;
                closeSideFrame();

                const form = window.top.document.body.appendChild(ev.target);

                form.style.display = 'none';
                form.submit();
            });
        });
    }

    // -- State-indicator pagetree dropdown menu ------------------------------

    function ajaxPost(event) {
        event.preventDefault();

        const element = event.currentTarget;
        const csrfToken = getCsrfToken();

        if (!csrfToken) {
            showError('CSRF token not found');
            return;
        }

        if (element.getAttribute('target') === '_top') {
            // Posting to target="_top" requires creating a form and submitting it.
            postViaForm(element.getAttribute('href'), csrfToken, true);
            return;
        }

        showLoader();
        fetch(element.getAttribute('href'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'csrfmiddlewaretoken=' + encodeURIComponent(csrfToken)
        }).then(function (response) {
            hideLoader();
            if (response.ok) {
                reloadAfterAction();
                return null;
            }

            return response.text().then(function (text) {
                showError(text || response.statusText);
            });
        }).catch(function () {
            hideLoader();
            showError('');
        });
    }

    function closeMenu() {
        document.querySelectorAll('.menu-cover').forEach(function (el) {
            el.remove();
        });
    }

    function openMenu(menuHtml) {
        const cover = document.createElement('div');

        closeMenu();
        cover.className = 'menu-cover cms-pagetree cms-pagetree-dropdown-menu-open';
        cover.innerHTML = menuHtml;
        document.body.appendChild(cover);

        const menu = cover.querySelector('.cms-pagetree-dropdown-menu');

        if (menu) {
            menu.querySelectorAll('.js-cms-tree-lang-trigger').forEach(function (el) {
                el.addEventListener('click', ajaxPost);
            });
        }

        return menu;
    }

    function initIndicatorMenu() {
        const triggers = document.querySelectorAll('.js-cms-pagetree-dropdown-trigger');

        if (!triggers.length) {
            return;
        }

        triggers.forEach(function (trigger) {
            trigger.addEventListener('click', function (event) {
                event.stopPropagation();
                event.preventDefault();

                const rect = trigger.getBoundingClientRect();
                const top = rect.top + window.scrollY;
                const left = rect.left + window.scrollX;
                const menu = openMenu(JSON.parse(trigger.dataset.menu));

                if (menu) {
                    // eslint-disable-next-line no-magic-numbers
                    menu.style.top = (top - 10) + 'px';
                    // eslint-disable-next-line no-magic-numbers
                    menu.style.right = (document.body.clientWidth - left + 10) + 'px';
                }
            });
        });
        document.addEventListener('click', closeMenu);
    }

    // -- Version-compare checkbox selection ----------------------------------

    let firstChecked;
    let lastChecked;

    function handleVersionSelection(event) {
        if (firstChecked instanceof HTMLInputElement && firstChecked.checked) {
            firstChecked.checked = false;
            firstChecked.closest('tr').classList.remove('selected');
            firstChecked = lastChecked;
        }

        if (event.target instanceof HTMLInputElement) {
            if (event.target.checked) {
                firstChecked = lastChecked;
                lastChecked = event.target;
            } else if (firstChecked === event.target) {
                firstChecked = null;
            } else {
                lastChecked = null;
            }
        }
    }

    function initVersionCompareSelection() {
        const selectedVersions = document.querySelectorAll('#result_list input[type="checkbox"].action-select');
        const selectElement = document.querySelector('#changelist-form select[name="action"]');

        if (selectElement instanceof HTMLSelectElement) {
            for (let i = 0; i < selectElement.options.length; i++) {
                if (selectElement.options[i].value && selectElement.options[i].value !== 'compare_versions') {
                    // For future safety: only constrain the selection when the
                    // sole bulk action is comparing versions.
                    return;
                }
            }
        }

        selectedVersions.forEach(function (selectedVersion) {
            selectedVersion.addEventListener('change', handleVersionSelection);
        });
    }

    // -- Bootstrap -----------------------------------------------------------

    function init() {
        initObjectToolButtons();
        initCloseSideframe();
        initIndicatorMenu();
        initVersionCompareSelection();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
