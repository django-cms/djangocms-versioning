window.addEventListener('load', function() {
  document.querySelector('select[name=action]').addEventListener('change', function() {
    var selectVal = this.options[this.selectedIndex].text;
    if (selectVal == "Compare versions"){
        window.onload = document.getElementById('changelist-form').setAttribute('target', '_blank');
    }
  })
})
