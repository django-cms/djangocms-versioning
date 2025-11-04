(function() {
    let firstChecked;
    let lastChecked;

    function handleVersionSelection(event) {
        if (firstChecked instanceof HTMLInputElement && firstChecked.checked) {
            firstChecked.checked = false;
            firstChecked.closest('tr').classList.remove('selected');
            firstChecked = lastChecked;
        }
        if (event.target instanceof HTMLInputElement) {
            if (event.target.checked) {
                firstChecked = lastChecked;
                lastChecked = event.target;
            } else if (firstChecked === event.target) {
                firstChecked = null;
            } else {
                lastChecked = null;
            }
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        const selectedVersions = document.querySelectorAll('#result_list input[type="checkbox"].action-select');
        const selectElement = document.querySelector('#changelist-form select[name="action"]');

        if (selectElement instanceof HTMLSelectElement) {
            for (let i = 0; i < selectElement.options.length; i++) {
                if (selectElement.options[i].value && selectElement.options[i].value !== 'compare_versions') {
                    // for future safety: do not restrict on two selected versions, since there might be other actions
                    return;
                }
            }
        }
        selectedVersions.forEach(function(selectedVersion) {
            selectedVersion.addEventListener('change', handleVersionSelection);
        });
    });
})();
