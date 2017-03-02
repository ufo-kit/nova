var app = new Vue({
  el: '#bookmarks',
  data: {
    token: readCookie('token'),
    bookmarked_datasets: [],
  },
  created: function() {
    var headers = {
      'Auth-Token': this.token
    }
    var api_str = '/api/user/'+username+'/bookmarks'
    this.$http.get(api_str, {headers: headers}).then((response) => {
      this.bookmarked_datasets = response.body
      console.log(response.body)
    })
  }
})
