function isEmpty(el) {
    return !$.trim(el.html())
}

$(document).ready(function () {
    $('select[name="signup_method_slug"]').on('change', function () {
        $.ajax({
            url: JSON.parse(document.getElementById('configuration_form_url').textContent).url.replace("slug", this.value),
            type: 'GET',

            success: function (data) {
                $('#configuration_form').html(data);
                handleForms($('#configuration_form'));
            }
        });
    });

    if (isEmpty($('#configuration_form'))) {
        $('select[name="signup_method_slug"]').trigger("change")
    }
});