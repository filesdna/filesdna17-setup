/** @odoo-module **/    
$(document).ready(function(){
    var screensize = screen.width;
    var base_url =$("input[name=base_url]").val();
    var status =$("input[name=status]").val();
    if (status == 'verified' || status == 'already_verified')
    {
        var counter = 4 ;
        $("#loadImgWrap").show();
        $("#second_counter").text('You will be redirected in '+ 5 + ' secs.');
        var myInterval = setInterval(function () {
        if (counter > 0)
        {
            $("#second_counter").text('You will be redirected in '+ counter+ ' secs.');

        }
        else{
            window.location = base_url +'/';
        }
        --counter;
    }, 1000);
    }
});