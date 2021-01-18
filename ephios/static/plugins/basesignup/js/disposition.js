$(document).ready(function () {
    $("[data-drop-to-state]").each(function (index, elem) {
        Sortable.create(elem, {
            group: "participations",
            sort: true,
            draggable: ".draggable",
            emptyInsertThreshold: 50,
            fallbackTolerance: 5,
            animation: 150,
            easing: "cubic-bezier(1, 0, 0, 1)",
            onAdd: function (event) {
                const newState = $(event.target).data("drop-to-state");
                $(event.item).find(".state-input").val(newState);
            },
        });
    });

    $("select#id_user[form='add-user-form']").change(function () {
        // Check input( $( this ).val() ) for validity here
        console.log($(this).val());
        const form = $("#" + $(this)[0].form.id);
        console.log(form);
        console.log(form.serialize());
        $.ajax({
            url: form.attr("action"),
            type: 'post',
            dataType: 'html',
            data: form.serialize(),
            success: function (data) {
                // adapted from addForm from formset.js, maybe open a PR for that?!
                const formset = $('#participation-form').formset('getOrCreate');
                const newIndex = formset.totalFormCount();

                const spawn = $("[data-formset-spawn]");
                const newFormHtml = data.replace(new RegExp(formset.opts.empty_prefix, 'g'), newIndex);
                const $newFormFragment = $($.parseHTML(newFormHtml));
                formset.$managementForm('TOTAL_FORMS').val(newIndex + 1);
                spawn.append($newFormFragment);

                var $newForm = $newFormFragment.filter(formset.opts.form);
                formset.bindForm($newForm, newIndex);

                var prefix = formset.formsetPrefix + '-' + newIndex;
                $newForm.find('[name=' + prefix + '-ORDER]').val(newIndex);
                $newForm.attr("data-formset-created-at-runtime", "true");
            }
        });

    });

});