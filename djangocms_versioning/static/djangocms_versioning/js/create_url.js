(function($) {
    $(function() {

        function initializeContentObjectWidget($element) {
            let endpoint = $element.attr('data-select2-url');
            let itemsPerPage = 30;

            $element.select2({
                formatAjaxError: function (jqXHR, textStatus, errorThrown) {
                    return "Loading failed, Please select content type first";
                    },
                minimumInputLength: 3,
                responmaximumInputLength: 20,
                ajax: {
                    url: endpoint,
                    dataType: 'json',
                    quietMillis: 250,
                    data: function(term, page) {
                        return {
                            page: page,
                            limit: itemsPerPage,
                            site: $(this.context)
                                .closest('fieldset')
                                .find('.field-site select')
                                .val(),
                            content_type_id: $(this.context)
                                .closest('fieldset')
                                .find('.field-content_type select')
                                .val(),
                            query: term,
                        };
                    },
                    results: function(data, page) {
                        return data;
                    }
                },
                initSelection: function(element, callback) {
                    var objectId = element.val();
                    var contentTypeId = element.closest('fieldset').find('select[id$="content_type"]').val();

                    $.ajax({
                        url: endpoint,
                        dataType: 'json',
                        data: {
                            pk: objectId,
                            content_type_id: contentTypeId,
                        }
                    })
                        .done(function(data) {
                            var text = objectId;
                            if (data.results.length) {
                                text = data.results[0].text;
                            }
                            callback({ id: objectId, text: text });
                        })
                        .fail(function() {
                            callback({ id: objectId, text: objectId });
                        });
                }
            });
        }
        $(':not([id*=__prefix__])[id$="object_id"]').each(function(i, element) {
            initializeContentObjectWidget($(element));
        });
        django
            .jQuery(document)
            .on('formset:added', function(event, $row, formsetName) {
                initializeContentObjectWidget($($row).find('[id$="object_id"]'));
            });
    });
})(CMS.$);