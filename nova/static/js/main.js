function readCookie(a) {
    var b = document.cookie.match('(^|;)\\s*' + a + '\\s*=\\s*([^;]+)');
    return b ? b.pop() : '';
}

var app = new Vue({
  el: '#search',
  data: {
    query: '',
    message: '',
    items: [],
    token: readCookie('token'),
  },
  watch: {
    query: function (data) {
      this.searchQuery (data)
    }
  },
  methods: {
    searchQuery: _.debounce(
      function (query) {
        var params = {
          q: query,
          token: this.token,
        }

        this.$http.get('/api/search', {params: params}).then((response) => {
          return response.json();
        }).then((items) => {
          this.items = items
        });
      },
      250
    )
  }
})
