(function($) {
    $(document).ready(function() {
        $('.cms-form-post-method').on('click', function(e) {
            e.preventDefault();
            const csrf_token = document.querySelector('form input[name="csrfmiddlewaretoken"]').value;
            const url = this.href;
            const $form = $('<form method="post" action="' + url + '"></form>');
            const $csrf = $(`<input type="hidden" name="csrfmiddlewaretoken" value="${csrf_token}">`);

            $form.append($csrf);
            $form.appendTo('body').submit();
        });
    });
})(django.jQuery);
