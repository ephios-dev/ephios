$(document).ready(function () {
    $("input:radio[name ='action']").change(function (event) {
        if ($("input:radio[name ='action']:checked").val() === "participants")
            $("#div_id_mail_content").slideDown();
        else
            $("#div_id_mail_content").slideUp();
    });

});
