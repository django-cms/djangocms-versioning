(function ($) {
    'use strict';

    let container;

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
        } catch (err) {}

        $.ajax({
            method: 'post',
            url: $(this).attr('href'),
            data: {csrfmiddlewaretoken: csrfToken }
        })
            .done(function() {
                try {
                    window.top.CMS.API.Toolbar.hideLoader();
                } catch (err) {}

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
                } catch (err) {}
                showError(error.responseText ? error.responseText : error.statusText);
            });
    }

    /**
     * Displays an error within the django UI.
     *
     * @method showError
     * @param {String} message string message to display
     */
    function showError(message) {
        let messages = $('.messagelist');
        let breadcrumb = $('.breadcrumbs');
        let reload = "Reload";
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

    function close_menu() {
        if (container) {
            container.find(".menu-cover").remove();
            container = false;
        }
    }

    function open_menu(menu) {
        close_menu();
        container = $("body");  // first parent with position: relative
        container.append('<div class="menu-cover cms-pagetree cms-pagetree-dropdown-menu-open"></div>');
        container.find(".menu-cover").html(menu);
        menu = container.find(".cms-pagetree-dropdown-menu");
        menu.find('.js-cms-tree-lang-trigger').click(
            ajax_post
        );
        return menu;
    }
    $(document).click(close_menu);
    $(function() {
        $('.js-cms-pagetree-dropdown-trigger').click(function(event) {
            event.stopPropagation();
            event.preventDefault();
            let menu = JSON.parse(this.dataset.menu);
            menu = open_menu(menu);
            const offset = $(this).offset();
            menu.css({
                top: offset.top - 10,
                right: container.width() - offset.left + 10
            });
         });
    });
})(django.jQuery);
