$(document).ready(function () {
    $("#btn_check").on('click', function () {
        $.ajax({
            url: JSON.parse(document.getElementById('rrule_url').textContent).url,
            type: 'POST',
            data: {"recurrence_string": $("#id_recurrence").val(), "dtstart": $("#id_start_date").val()},
            headers: {"X-CSRFToken": getCookie("csrftoken")},

            success: function (data) {
                $("#rrule_occurrences_heading").html(gettext("Currently selected dates"));
                if (data) {
                    data = JSON.parse(data)
                    if (Array.isArray(data) && data.length) {
                        $('#rrule_occurrences').html(data.join("<br>"));
                        return;
                    }
                }
                $('#rrule_occurrences').html("<p>" + gettext("No dates selected") + "</p>");
            }
        });
    });
});

function parseIsoDatetime(dtstr) {
    var dt = dtstr.split(/[: T-]/).map(parseFloat);
    return new Date(dt[0], dt[1] - 1, dt[2], dt[3] || 0, dt[4] || 0, dt[5] || 0, 0);
}
