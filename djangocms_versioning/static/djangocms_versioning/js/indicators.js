(function ($) {
    'use strict';

    let container;

    /**
     * Displays an error within the django UI.
     *
     * @method showError
     * @param {String} message string message to display
     */
    function showError(message) {
        let messages = $('.messagelist');
        let breadcrumb = $('.breadcrumbs');

        let tpl =
            '' +
            '<ul class="messagelist">' +
            '   <li class="error">' +
            '       {msg} ' +
            '   </li>' +
            '</ul>';
        const error = window.top.CMS?.config?.lang?.error || '';
        let msg = tpl.replace('{msg}', '<strong>' + error + '</strong> ' + message);

        if (messages.length) {
            messages.replaceWith(msg);
        } else {
            breadcrumb.after(msg);
        }
    }

    function ajax_post(event) {
        event.preventDefault();
        const element = $(this);
        let csrfToken = window.CMS?.config?.csrf || $('input[name="csrfmiddlewaretoken"]').val();

        if (!csrfToken) {
            // Finally try cookies
            const cookieToken = document.cookie.match(/csrftoken=([^;]*);?/);

            if (cookieToken && cookieToken.length > 1) {
                csrfToken = cookieToken[1];
            } else {
                showError('CSRF token not found');
                return;
            }
        }

        if (element.attr('target') === '_top') {
            // Post to target="_top" requires to create a form and submit it
            const parent = window.top;

            $('<form method="post" action="' + element.attr('href') + '">' +
                '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken + '"></form>')
                .appendTo($(parent.document.body))
                .submit();
            return;
        }
        try {
            window.top.CMS.API.Toolbar.showLoader();
        } catch {}

        $.ajax({
            method: 'post',
            url: $(this).attr('href'),
            data: { csrfmiddlewaretoken: csrfToken }
        })
            .done(function() {
                try {
                    window.top.CMS.API.Toolbar.hideLoader();
                } catch {}

                if (window.self === window.top) {
                    // simply reload the page
                    window.location.reload();
                } else {
                    window.top.CMS.API.Helpers.reloadBrowser('REFRESH_PAGE');
                }
            })
            .fail(function(error) {
                try {
                    window.top.CMS.API.Toolbar.hideLoader();
                } catch {}
                showError(error.responseText ? error.responseText : error.statusText);
            });
    }

    function close_menu() {
        if (container) {
            container.find('.menu-cover').remove();
            container = false;
        }
    }

    /**
     * Opens a dropdown menu and displays it on the page.
     *
     * This function first closes any currently open menus, then appends a
     * menu cover to the body. The provided menu content is inserted into
     * the menu cover, and event listeners are attached to language triggers
     * within the menu for AJAX functionality.
     *
     * @param {string} menu - The HTML content to be displayed in the dropdown menu.
     * @returns {jQuery} The jQuery object representing the menu container.
     */
    function open_menu(menu) {
        close_menu();
        container = $('body'); // first parent with position: relative
        container.append('<div class="menu-cover cms-pagetree cms-pagetree-dropdown-menu-open"></div>');
        container.find('.menu-cover').html(menu);
        const menu_container = container.find('.cms-pagetree-dropdown-menu');

        menu_container.find('.js-cms-tree-lang-trigger').click(
            ajax_post
        );
        return menu_container;
    }
    $(document).click(close_menu);
    $(function() {
        $('.js-cms-pagetree-dropdown-trigger').click(function(event) {
            event.stopPropagation();
            event.preventDefault();
            const offset = $(this).offset();
            let menu = JSON.parse(this.dataset.menu);

            menu = open_menu(menu);
            menu.css({
                // eslint-disable-next-line no-magic-numbers
                top: offset.top - 10,
                // eslint-disable-next-line no-magic-numbers
                right: container.width() - offset.left + 10
            });
        });
    });
})(django.jQuery);
