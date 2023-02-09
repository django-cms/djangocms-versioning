(function ($) {
    var container;

    function ajax_post(event) {
        event.preventDefault();
        var element = $(this);
        if (element.closest('.cms-pagetree-dropdown-item-disabled').length) {
            return;
        }
        var csrfToken = document.cookie.match(/csrftoken=([^;]*);?/)[1];

        if (element.attr('target') === '_top') {
            // Post to target="_top" requires to create a form and submit it
            var parent = window;

            if (window.parent) {
                parent = window.parent;
            }
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
                    _reloadHelper();
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
        var messages = $('.messagelist');
        var breadcrumb = $('.breadcrumbs');
        var reload = "Reload";
        var tpl =
            '' +
            '<ul class="messagelist">' +
            '   <li class="error">' +
            '       {msg} ' +
            '       <a href="#reload" class="cms-tree-reload"> ' +
            reload +
            ' </a>' +
            '   </li>' +
            '</ul>';
        var msg = tpl.replace('{msg}', '<strong>' + window.top.CMS.config.lang.error + '</strong> ' + message);

        if (messages.length) {
            messages.replaceWith(msg);
        } else {
            breadcrumb.after(msg);
        }
        $("a.cms-tree-reload").click(function (e) {
            e.preventDefault();
            _reloadHelper();
        });
    }

    /**
     * Checks if we should reload the iframe or entire window. For this we
     * need to skip `CMS.API.Helpers.reloadBrowser();`.
     *
     * @method _reloadHelper
     * @private
     */
    function _reloadHelper() {
        if (window.self === window.top) {
            CMS.API.Helpers.reloadBrowser();
        } else {
            window.location.reload();
        }
    }

    function close_menu() {
        if (container) {
            container.find(".menu-cover").remove();
            container = false;
        }
    }

    function open_menu(menu) {
        var menu;
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
            var menu = JSON.parse(this.dataset.menu);
            menu = open_menu(menu);
            var offset = $(this).offset();
            menu.css({
                top: offset.top - 10,
                right: container.width() - offset.left + 10
            });
         });
    });
})(django.jQuery);
