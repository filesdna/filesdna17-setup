$(function (require) {
//    "use strict";

    $(document).ready(function() {
    $('#domain_chain_crt_alert').hide();
    $('#domain_crt_alert').hide();
    $('#domain_key_alert').hide();
    $('#domain_key_val_alert').hide();
    $('#domain_crt_val_alert').hide();
    $('#domain_chain_crt_val_alert').hide();
    $('#web_conf_val').hide();
    var rpc = require('web.rpc');
    var web_conf_val = $('#web_conf_val').text();
    var type ='http'
    var db_name


    $('#cancel_btn').on('click',function(){
        document.getElementById("domain_form").reset();
        $('#myModal').hide();
        window.location.reload();
    });

    $('.domain_btn').on('click',function(){
        document.getElementById("domain_form").reset();
        db_name = $(this).parent().attr('id')
        $('#myModal').show();
        $('#db_name').val(db_name)
        $('#domain').val(type)
    });
    $('#domain_type ').change(function(){
        type = this.value
        $('#domain').val(type)
        if (type == 'https'){
            $('.https_tr').removeAttr('style')
            $('#domain_key').attr('required','True')
            $('#domain_crt').attr('required','True')
            // if (web_conf_val == 'nginx'){
            // $('#domain_chain_crt').attr('required','True')
            // };
            if (web_conf_val == 'apache'){
            $('#domain_chain_crt').removeAttr('required')
            };
        };
        if (type == 'http'){
            $('.https_tr').hide();
            $('#domain_key').removeAttr('required')
            $('#domain_crt').removeAttr('required')
            $('#domain_chain_crt').removeAttr('required')
        };
    });
    $('#domain_form').submit(function(e){
        $('#myModal').hide();
        window.location.reload();
    });
    var key_data = false;
    var crt_data = false;
    var chain_crt_data = false;
    var domainKeyFileSelector = document.getElementById('domain_key');
    if(domainKeyFileSelector){domainKeyFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_key_text', text);
                };
                
                reader.readAsText(fileList[0]);
            });
        }
            var domainCrtFileSelector = document.getElementById('domain_crt');
            if(domainCrtFileSelector){domainCrtFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_crt_text', text);
                };
                reader.readAsText(fileList[0]);
            });
        }
            var domainChainCrtFileSelector = document.getElementById('domain_chain_crt');
            
            if(domainCrtFileSelector){domainChainCrtFileSelector.addEventListener('change', (event) => {
                const fileList = event.target.files;
                var reader = new FileReader();
                reader.onload = function(){
                var text = reader.result;
                reader.result.substring(0, 200);
                sessionStorage.setItem('domain_chain_crt_text', text);
                };
                reader.readAsText(fileList[0]);
            });

        }
            // var sdata = false;
            $('#domain_key').on('change', function () {
                // const fileList = this.target.files;
                var fileReader = new FileReader();
                fileReader.onload = function () {
                    key_data = fileReader.result;  // data <-- in this var you have the file data in Base64 format
                    key_data = key_data.split(';base64,')[1];
                };
                fileReader.readAsDataURL($('#domain_key').prop('files')[0]);
            });
            $('#domain_crt').on('change', function () {
                var fileReader = new FileReader();
                fileReader.onload = function () {
                    crt_data = fileReader.result;  // data <-- in this var you have the file data in Base64 format
                    crt_data = crt_data.split(';base64,')[1];
                };
                fileReader.readAsDataURL($('#domain_crt').prop('files')[0]);
            });
            $('#domain_chain_crt').on('change', function () {
                var fileReader = new FileReader();
                fileReader.onload = function () {
                    chain_crt_data = fileReader.result;  // data <-- in this var you have the file data in Base64 format
                    chain_crt_data = chain_crt_data.split(';base64,')[1];
                };
                fileReader.readAsDataURL($('#domain_chain_crt').prop('files')[0]);
            });


    $('#submit_btn').on('click',function(){
            
          var domain_key_text = sessionStorage.getItem('domain_key_text');
          console.log("domain_key_text",domain_key_text)
          var domain_crt_text = sessionStorage.getItem('domain_crt_text');
          var domain_chain_crt_text = sessionStorage.getItem('domain_chain_crt_text');
          var string1 = '-----BEGIN CERTIFICATE-----'
          var string2 = '-----END CERTIFICATE-----'

          var key_string1 = '-----BEGIN PRIVATE KEY-----'
          var key_string2 = '-----END PRIVATE KEY-----'
          if (domain_key_text){
            var domain_key_first_text = domain_key_text.split('\n')[0];
            console.log('domain key >>>',domain_key_first_text)
            var key_result = domain_key_first_text.localeCompare(key_string1)
            console.log('key result',key_result)
          };
          if (domain_crt_text){
            var domain_crt_first_text = domain_crt_text.split('\n')[0];
            var crt_result = domain_crt_first_text.localeCompare(string1)
          };
          if(domain_chain_crt_text){
            var domain_chain_first_text = domain_chain_crt_text.split('\n')[0];
            var chain_result = domain_chain_first_text.localeCompare(string1)
          };
          var client_domain = document.getElementById('client_domain').value
          var domain_key = $('#domain_key').val()
          var domain_crt = $('#domain_crt').val()
          var domain_chain_crt = $('#domain_chain_crt').val()
          var domain_chain_crt_ext = domain_chain_crt.split('.').pop()
          var client_domain_val = $('#client_domain').val()
            if (type == 'https'){
            console.log(" type httpss");
                if(domain_crt && domain_key)
                {domain_key
                    var domain_key_ext = domain_key.split('.').pop()
                    console.log("domain key >>>>>>",domain_key)
                    console.log("domain keyext >>>>>>",domain_key_ext)
                    var domain_crt_ext = domain_crt.split('.').pop()
                    console.log("domain crt >>>>>>",domain_crt)
                    console.log("domain crt >>>>>>",domain_crt_ext)
                    var tenant_id = document.querySelector('button[name="add_domain"]').value;


                    if (domain_crt_ext == 'crt' && domain_key_ext == 'key')
                    {
                        $('#domain_key_alert').hide();
                        $('#domain_crt_alert').hide();
                        if ((domain_key_text.includes(key_string1))  && (domain_key_text.includes(key_string2)) && (domain_crt_text.includes(string1)) && (domain_crt_text.includes(string2)))
                        {   
                            rpc.query({
                                model: 'domain.masking.details',
                                method: 'create_domain_masking_details',
                                args: [[client_domain,key_data,crt_data,chain_crt_data,tenant_id,domain_key,domain_crt,domain_chain_crt]],
                            }).then(function (res) {
                                alert("Domain Added Successfully!!")
                                window.location.reload();
                            });
                            
                            $('#domain_key_val_alert').hide();
                            $('#domain_crt_val_alert').hide();
                            if (domain_chain_crt)
                            {
                                    if (domain_chain_crt)
                                    {

                                        if(domain_chain_crt_ext == 'crt'){

                                            $('#domain_chain_crt_alert').hide();
                                             if (domain_chain_crt_text.includes(string2)  && chain_result == 0)
                                             {
                                                   $('#domain_chain_crt_val_alert').hide();
                                                   $('#submit_btn').attr("type", "submit");
                                             }
                                             else{
                                                $('#domain_chain_crt_val_alert').show();
                                             };
                                        }
                                        else
                                        {
                                            $('#domain_chain_crt_alert').show();
                                        };
                                    };

                            }
                            else{
                                $('#submit_btn').attr("type", "submit");
                            };

                        }
                        else
                        {   
                            
                            if((!(domain_key_text.includes(key_string1)))  || (!(domain_key_text.includes(key_string2))))
                            {

                                $('#domain_key_val_alert').show();
                            }
                            else{
                                $('#domain_key_val_alert').hide();
                            };
                            if((!(domain_crt_text.includes(string1)))  || (!(domain_crt_text.includes(string2))))
                            {

                                $('#domain_crt_val_alert').show();
                            }
                            else{
                                $('#domain_crt_val_alert').hide();
                            };
                        };
                    }
                    else{
                        if(domain_crt_ext !== 'crt')
                        {
                            $('#domain_crt_alert').show();
                        }
                        else
                        {
                            $('#domain_crt_alert').hide();
                        };
                        if (domain_key_ext !== 'key')
                        {
                            $('#domain_key_alert').show();
                        }
                        else
                        {
                             $('#domain_key_alert').hide();
                        };
                        if (domain_chain_crt && domain_chain_crt_ext !== 'crt')
                        {
                            $('#domain_chain_crt_alert').show();
                        }
                        else
                        {
                            if (web_conf_val == 'nginx')
                            {
                                 $('#domain_chain_crt_alert').hide();
                            };
                        };
                    };
                }

                else{

                    $('#submit_btn').attr("type", "submit");
                };
            };

            if (type == 'http'){
            $('#submit_btn').attr("type", "submit");
            };

    });
});
});