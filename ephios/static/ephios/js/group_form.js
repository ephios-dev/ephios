function handleGroupForm(ev) {
    const planningGroupCheckbox = $("#id_is_planning_group");
    if ($("#id_is_management_group").is(":checked")) {
        $("#id_is_hr_group").prop("disabled", true).prop("checked", true);
        planningGroupCheckbox.prop("disabled", true).prop("checked", true);
    } else {
        $("#id_is_hr_group").prop("disabled", false);
        planningGroupCheckbox.prop("disabled", false);
    }

    const slidingOptions = {};
    if (!ev) {
        slidingOptions.duration = 0
    }

    if (planningGroupCheckbox.is(":checked")) {
        $(".publish-select").slideDown(slidingOptions);
    } else {
        $(".publish-select").slideUp(slidingOptions);
    }
}

$(document).ready(function () {
    $("#id_is_planning_group, #id_is_management_group").click(handleGroupForm);
    handleGroupForm();
});