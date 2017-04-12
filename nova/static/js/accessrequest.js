var app = new Vue({
  el: '#request-access',
  data: {
    token: readCookie('token'),
    read: permissions.read,
    interact: permissions.interact,
    fork: permissions.fork,
    message: ''
  },
  watch: {
    read: function() {
      if (!this.read) this.interact = false
    },
    interact: function() {
      if (this.interact) this.read = true
      else this.fork = false
    },
    fork: function() {
      if (this.fork) this.interact = true
    }
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
      var api_str = '/api/'+object_type+'/'+object_id+'/accessreq/'+user_id
      console.log(api_str)
      this.$http.put(api_str, request_data, {headers: headers}).then((response) => {
        if(response.status == 200 || response.status == 201)
          window.location = '/'
      })
    }
  }
})
