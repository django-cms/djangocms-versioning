window.addEventListener('load', function() {
  document.querySelector('select[name=action]').addEventListener('change', function() {
    var selectVal = this.options[this.selectedIndex].text;
    if (selectVal == "Compare versions"){
        // Setting the target to blank to ensure the compare view is opened in a new tab
        window.onload = document.getElementById('changelist-form').setAttribute('target', '_blank');
        var buttonElement = document.querySelector("button")
        // Reloading the page to renew the csrf token which prevented multiple version compare tabs from opening
        if (buttonElement.innerHTML == "Go") {
            buttonElement.setAttribute("onclick", "window.location.reload();");
        }
    }
  })
})
