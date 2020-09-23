function isEmpty(el) {
    return !$.trim(el.html())
}

$('select[name="signup_method_slug"]').on('change', function () {
    $.ajax({
        url: JSON.parse(document.getElementById('configuration_form_url').textContent).url.replace("slug", this.value),
        type: 'GET',

        success: function (data) {
            $('#configuration_form').html(data);
            $('.django-select2').djangoSelect2();
        }
    });
});

$(document).ready(function () {
    if (isEmpty($('#configuration_form'))) {
        $('select[name="signup_method_slug"]').trigger("change")
    }
});