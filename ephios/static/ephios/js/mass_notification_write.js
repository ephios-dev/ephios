$(document).ready(function () {
    const jSelect = $("#id_to_participants");
    const confirmedIDs = $("#btn-participants-confirmed").data("participants").trim().split(" ")
    const requestedIDs = $("#btn-participants-requested").data("participants").trim().split(" ")

    function formatState(state) {
        let $state = $('<span><span></span></span>');
        const span = $state.find("span");
        span.text(state.text);
        if (confirmedIDs.indexOf(state.id) >= 0) {
            span.addClass("text-success");
        } else if (requestedIDs.indexOf(state.id) >= 0) {
            span.addClass("text-warning");
        }
        return $state;
    }

    jSelect.select2({
            templateSelection: formatState,
            sorter: data => data.sort((a, b) => a.text.localeCompare(b.text))
        }
    )
    Array.from(document.getElementsByClassName("btn-add-recipients")).forEach(button => {
        button.addEventListener("click", function (e) {
            e.preventDefault();
            const namesToSelect = button.dataset.participants.trim().split(" ");
            jSelect.val(jSelect.val().concat(namesToSelect)).trigger('change');
        })
    });
});
