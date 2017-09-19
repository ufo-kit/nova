var app = new Vue({
  el: '#request-access',
  data: {
    token: readCookie('token'),
    read: permissions.read,
    interact: permissions.interact,
    fork: permissions.fork,
    message: ''
  },
  methods: {
    requestAccess: function() {
      var headers = {
        'Auth-Token': this.token
      }
      var request_data = {
        'permissions': {
          'read': this.read,
          'interact': this.interact,
          'fork': this.fork }, 
        'message': this.message }
      var user_id = this.token.split('.')[0]
      var api_str = '/api/datasets/' + user_name + '/' + dataset_name + '/request'
      console.log(api_str)
      this.$http.put(api_str, request_data, {headers: headers}).then((response) => {
        if(response.status == 200 || response.status == 201)
          window.location = '/'
      })
    }
  }
})
