
$(function () {
  $('[data-toggle="tooltip"]').tooltip()
})

$('#formset').on('formAdded', function(event) {
    $(event.target).find("select").first().djangoSelect2()
});