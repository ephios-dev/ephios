$(document).ready(function () {
    $('[data-toggle="tooltip"]').tooltip();

    $("[data-formset]").formset({
        animateForms: true,
        reorderMode: 'dom',
    }).on("formAdded", "div", function (event) {
        $(event.target).find(".django-select2").first().djangoSelect2()
    });

    const language = $("body").data("language")
    const language_urls = {"de-de": ""}
    $(".datatable").DataTable({
        "paging": false,
        "info": false,
        "responsive": true,
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
})
