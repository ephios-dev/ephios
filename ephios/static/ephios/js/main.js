$(document).ready(function () {
    $('[data-toggle="tooltip"]').tooltip();

    $("[data-formset]").formset({
        animateForms: true,
        reorderMode: 'dom',
    }).on("formAdded", "div", function (event) {
        $(event.target).find(".django-select2").first().djangoSelect2()
    });

    $(".datatable").DataTable({
        "paging": false,
        "info": false,
        "responsive": true,
        "language": {
            "url": $("#datatables-script").data("datatables-translation-url")
        }
    });

    $("[data-drop-to-state]").each(function (index, elem) {
        Sortable.create(elem, {
            group: "participations",
            sort: false,
            draggable: ".draggable",
            emptyInsertThreshold: 50,
            animation: 150,
            easing: "cubic-bezier(1, 0, 0, 1)",
            onAdd: function (event) {
                const newState = $(event.target).data("drop-to-state");
                $(event.item).find(".state-input").val(newState);
            },
        });
    });

    var recurrenceFields = document.querySelectorAll('.recurrence-widget');
    Array.prototype.forEach.call(recurrenceFields, function(field, index) {
        new recurrence.widget.Widget(field.id, {});
    });
})

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}