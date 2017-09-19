function readCookie(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

$(document).ready(function(){
        $('[data-toggle="tooltip"]').tooltip();
      });
