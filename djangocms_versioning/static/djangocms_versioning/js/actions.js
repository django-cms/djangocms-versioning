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

                var fakeForm = $(
                    '<form style="display: none" action="' + action.attr('href') + '" method="POST">"' +
                        '<input type="hidden" name="csrfmiddlewaretoken" value="' +
                            document.cookie.match(/csrftoken=([^;]*);?/)[1] +
                        '">' +
                    '</form>'
                );
                var keepSideFrame = action.attr('class').indexOf('js-versioning-keep-sideframe') !== -1
                // always break out of the sideframe, cause it was never meant to open cms views inside it
                try {
                    if (!keepSideFrame)
                    {
                        window.top.CMS.API.Sideframe.close();
                    }
                } catch (err) {}
                if (keepSideFrame) {
                   var document = window.document
                }
                else {
                   var document = window.top.document
                }
                fakeForm.appendTo(document.body).submit();
            });

        $('.js-versioning-close-sideframe').on('click', function () {
            try {
                window.top.CMS.API.Sideframe.close();
            } catch (e) {}
        });
    });

})((typeof django !== 'undefined' && django.jQuery) || (typeof CMS !== 'undefined' && CMS.$) || false);
