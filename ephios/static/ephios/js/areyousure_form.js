$(document).ready(function () {
    $('form').areYouSure();
    // Listener for inputs that can dynamically add new forms and trigger a scan of the new form
    $('.add-form').click(function() {
        $('form').trigger('reinitialize.areYouSure');
      });
});