(function($) {
    if (!$) {
        return;
    }

    $(function() {
        // it is not possible to put a form inside a form, so
        // the versioning actions have to create their own form on click
        $('.js-versioning-action, .cms-versioning-js-publish-btn, .cms-versioning-js-edit-btn')
            .on('click', function(e) {
                e.preventDefault();

                var action = $(e.currentTarget);
                var formMethod = action.attr('class').indexOf('cms-action-method-get') !== -1 ? 'GET': 'POST';
                var csrfToken = formMethod == 'GET' ? '' : '<input type="hidden" name="csrfmiddlewaretoken" value="' +
                            document.cookie.match(/csrftoken=([^;]*);?/)[1] + '">';
                var fakeForm = $(
                    '<form style="display: none" action="' + action.attr('href') + '" method="' +
                           formMethod + '">' + csrfToken +
                    '</form>'
                );
                var keepSideFrame = action.attr('class').indexOf('js-versioning-keep-sideframe') !== -1;
                // always break out of the sideframe, cause it was never meant to open cms views inside it
                try {
                    if (!keepSideFrame)
                    {
                        window.top.CMS.API.Sideframe.close();
                    }
                } catch (err) {}
                if (keepSideFrame) {
                    var body = window.document.body;
                } else {
                    var body = window.top.document.body;
                }
                fakeForm.appendTo(body).submit();
            });

        $('.js-versioning-close-sideframe').on('click', function () {
            try {
                window.top.CMS.API.Sideframe.close();
            } catch (e) {}
        });
    });

})((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
