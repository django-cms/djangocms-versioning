(function($) {
    $(document).ready(function() {
        $('.cms-form-post-method').on('click', function(e) {
            e.preventDefault();
            var csrf_token = document.querySelector('form input[name="csrfmiddlewaretoken"]').value;
            var url = this.href;
            var $form = $('<form method="post" action="' + url + '"></form>');
            var $csrf = $(`<input type="hidden" name="csrfmiddlewaretoken" value="${csrf_token}">`);
            $form.append($csrf);
            $form.appendTo('body').submit();
        });
    });
})(django.jQuery);
