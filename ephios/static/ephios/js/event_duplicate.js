$("#id_recurrence").on('input', function () {
    $.ajax({
        url: JSON.parse(document.getElementById('rrule_url').textContent).url,
        type: 'POST',
        data: {"recurrence_string": $("#id_recurrence").val()},
        headers: {"X-CSRFToken": getCookie("csrftoken")},

        success: function (data) {
            $('#rrule_occurrences').html(data);
        }
    });
});