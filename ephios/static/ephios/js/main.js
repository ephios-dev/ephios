$(function () {
    $('[data-toggle="tooltip"]').tooltip();

    $("[data-formset]").formset({
        animateForms: true,
        reorderMode: 'dom',
    }).on("formAdded", "div", function (event) {
        $(event.target).find(".django-select2").first().djangoSelect2()
    });
})
