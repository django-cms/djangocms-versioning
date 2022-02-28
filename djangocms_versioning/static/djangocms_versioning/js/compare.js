window.addEventListener('load', function() {
  document.querySelector('select[name=action]').addEventListener('change', function() {
    let selectVal = this.options[this.selectedIndex].getAttribute("value");
    if (selectVal == "compare_versions") {
        const actionsForm = document.getElementById('changelist-form')
        // Setting the target to blank to ensure the compare view is opened in a new tab
        actionsForm.setAttribute('target', '_blank');
        const submitButton = actionsForm.querySelector('[type="submit"]')
        // Reloading the page to renew the csrf token which prevented multiple version compare tabs from opening
        submitButton.addEventListener("click", function (e) {
            window.location.reload()
        });
    }
  })
})
