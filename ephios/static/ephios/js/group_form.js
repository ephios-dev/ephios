$(document).ready(function () {
    $("#id_is_planning_group").click(function (event) {
        if ($(this).is(":checked"))
            $(".publish-select").slideDown();
        else
            $(".publish-select").slideUp();
    });
    if (!$("#id_is_planning_group").is(":checked")) {
        $(".publish-select").slideUp();
    }
});