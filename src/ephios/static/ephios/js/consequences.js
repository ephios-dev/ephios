$(document).ready(function () {
    $(".btn-consequence").click(function (event) {
        event.preventDefault(); //so that we stop normal form submit.
        const btn = $(this);
        const form = btn.closest("form");
        form.find(".btn-consequence").prop("disabled", true);
        $.ajax({
            url: form.attr('action'),
            type: 'post',
            dataType: 'json',
            data: form.serialize() + "&" + $(this).attr("name") + "=" + $(this).val(),
            success: function (data) {
                if (data.state !== "failed") {
                    btn.closest(".list-group-item").slideUp();
                } else {
                    message("danger", "There was an error processing this: " + data.fail_reason)
                    btn.closest(".list-group-item").slideUp();
                    // form.find(".btn-consequence").prop("disabled", false);
                }
            }
        });
    })
})
;