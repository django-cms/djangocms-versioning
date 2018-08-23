(function ($) {
    $(function () {
        // it is not possible to put a form inside a form, so
        // the versioning actions have to create their own form on click
        $('.js-versioning-action').on('click', function (e) {
            e.preventDefault();

            var action = $(e.currentTarget);

            var fakeForm = $('<form style="display: none" action="' + action.attr('href') + '" method="POST">"' +
                '<input type="hidden" name="csrfmiddlewaretoken" value="' + document.cookie.match(/csrftoken=([^;]*);?/)[1] + '">' +
            '</form>');

            fakeForm.appendTo(document.body).submit();
        });
    });
})(django.jQuery);
