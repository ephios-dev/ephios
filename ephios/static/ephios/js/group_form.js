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
    $("#id_is_management_group").click(function (event) {
        if ($(this).is(":checked")) {
            $("#id_is_hr_group").prop("disabled", true);
            $("#id_is_hr_group").prop("checked", true);
            $("#id_is_planning_group").prop("disabled", true);
            $("#id_is_planning_group").prop("checked", true);
            $(".publish-select").slideDown();
        }
        else {
            $("#id_is_hr_group").prop("disabled", false);
            $("#id_is_hr_group").prop("checked", false);
            $("#id_is_planning_group").prop("disabled", false);
            $("#id_is_planning_group").prop("checked", false);
            $(".publish-select").slideUp();
        }
    });
    if ($("#id_is_management_group").is(":checked")) {
        $("#id_is_hr_group").prop("disabled", true);
        $("#id_is_planning_group").prop("disabled", true);
    }
});