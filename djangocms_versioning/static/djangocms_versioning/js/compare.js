window.addEventListener('load', function() {
  document.querySelector('select[name=action]').addEventListener('change', function() {
    var selectVal = this.options[this.selectedIndex].text;
    if (selectVal == "Compare versions"){
        window.onload = document.getElementById('changelist-form').setAttribute('target', '_blank');
        var buttonElement = document.querySelector("button")
        if (buttonElement.innerHTML == "Go") {
            buttonElement.setAttribute("onclick", "window.location.reload();");
        }
    }
  })
})
