var app = new Vue({
  el: '#access-requests',
  data: {
    token: readCookie('token'),
    access_requests: [],
  },
  created: function() {
    var headers = {
      'Auth-Token': this.token
    }
    var api_str = '/api/accessreqs'
    this.$http.get(api_str, {headers: headers}).then((response) => {
      this.access_requests = response.body
    })
  }
})
