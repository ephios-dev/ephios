$(document).ready(function () {
    $("#id_can_add_event").click(function (event) {
        if ($(this).is(":checked"))
            $(".publish-select").slideDown();
        else
            $(".publish-select").slideUp();
    });
    if (!$("#id_can_add_event").is(":checked")) {
        $(".publish-select").slideUp();
    }
});