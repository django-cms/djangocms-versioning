function bindHandlers(submitButton){
    // Reloading the page to renew the csrf token which prevented multiple version compare tabs from opening
    submitButton.addEventListener("click", function (e) {
        window.location.reload()
    });
}

window.addEventListener('load', function() {
  document.querySelector('select[name=action]').addEventListener('change', function() {
    // Always set handlersBound to false when the select option changed
    let handlersBound = false;
    let selectVal = this.options[this.selectedIndex].getAttribute("value");
    const actionsForm = document.getElementById('changelist-form')
    const submitButton = actionsForm.querySelector('[type="submit"]')

    if (selectVal == "compare_versions") {
        // Setting the target to blank to ensure the compare view is opened in a new tab
        actionsForm.setAttribute('target', '_blank');
        if (handlersBound === false) {
            bindHandlers(submitButton);
            handlersBound = true
        }
    }else {
        // If the user deselect the compare version action, the "target=_blank" is removed
        actionsForm.removeAttribute('target');
    }
  })
})
