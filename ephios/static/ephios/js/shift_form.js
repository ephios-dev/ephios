function isEmpty(el) {
    return !$.trim(el.html())
}

$(document).ready(function () {
    const flowSelect = $('select[name="signup_flow_slug"]');
    flowSelect.on('change', function () {
        $.ajax({
            url: JSON.parse(document.getElementById('configuration_form_url').textContent).url.replace("METHOD_SLUG", this.value),
            type: 'GET',

            success: function (data) {
                const form = $('#flow_configuration_form');
                form.html(data);
                handleForms(form);
            }
        });
    });

    if (isEmpty($('#flow_configuration_form'))) {
        flowSelect.trigger("change")
    }
});