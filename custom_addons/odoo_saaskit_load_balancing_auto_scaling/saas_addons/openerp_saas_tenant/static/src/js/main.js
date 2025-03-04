$(function (require) {
  "use strict";
  const ajax = require('web.ajax');

  $(document).ready(function () {
    ajax:({
      url: '/check_login_user',
      dataType: 'json',
      success: function (data) {
        if (!data.result) {
          setTimeout(function () {
            $('.o_debug_manager').remove();
          }, 100);
        }
      },
      error: function (error) {
        console.error('Error:', error);
      }
    });
  });
});
