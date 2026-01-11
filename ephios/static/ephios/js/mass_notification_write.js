$(document).ready(function () {
    const jSelect = $("#id_to_participants");

    jSelect.select2({
            closeOnSelect: false
        }
    )

    document.getElementById("id_to_participants").addEventListener("invalid", (event) => {
        new bootstrap.Collapse('#collapseToParticipants').show();
    });

    Array.from(document.getElementsByClassName("check-add-recipients")).forEach(check => {
        check.addEventListener("click", function (e) {
            const namesToSelect = check.dataset.participants.trim().split(" ");
            if (check.checked) {
                jSelect.val(jSelect.val().concat(namesToSelect)).trigger('change');
            } else {
                jSelect.val(jSelect.val().filter(item => {
                    // keep items not in namesToSelect
                    return namesToSelect.indexOf(item) < 0;
                })).trigger('change');
            }
        });
    });
    jSelect.on("change", function (e) {
        Array.from(document.getElementsByClassName("check-add-recipients")).forEach(check => {
            const namesToSelect = check.dataset.participants.trim().split(" ");
            const namesSelected = jSelect.val().filter(item => {
                return namesToSelect.indexOf(item) >= 0;
            });
            if (namesSelected.length === 0) {
                check.indeterminate = false;
                check.checked = false;
            } else if (namesSelected.length === namesToSelect.length) {
                check.indeterminate = false;
                check.checked = true;
            } else {
                check.indeterminate = true;
                check.checked = true;
            }
        });
    });

});
