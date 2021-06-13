$(document).ready(function () {
    function handleMessageContentField(event) {
        const duration = event? 400 :0;
        if ($("input:radio[name ='action']:checked").val() === "participants")
            $("#div_id_mail_content").slideDown(duration);
        else
            $("#div_id_mail_content").slideUp(duration);
    }
    $("input:radio[name ='action']").change(handleMessageContentField);
    handleMessageContentField();
});
