Vue.component('searchresults', {
  template: '#search-results-template',
  props: ['show', 'search_query'],
  methods: {
    showFullResults: function() {
      this.$parent.$options.methods.showFullResults()
    }
  }
})

var mainsearch = new Vue ({
  el:'#main-search',
  data: {
    token: readCookie('token'),
    search_query: '',
    search_results: [],
  },
  watch: {
    search_query: function (data) {
      if (data == '')
        this.search_results = []
      else
        this.searchQuery(data)
    }
  },
  methods: {
    searchQuery: _.debounce(
      function (query) {
        var params = {
          q: query
        }
        var headers = {
            'Auth-Token': this.token
        }
        this.$http.get('/api/search', {params: params, headers: headers}).then((response) => {
          return response.json();
        }).then((items) => {
          this.search_results = items
        })
      },
      250
    ),
    showFullResults: function(query) {
      window.location = "/search?q=" + this.search_query
    },
    clearQuery: function () {
      this.search_query = ''
      this.search_results = []
    },
    haveSearchResults: function () {
      return this.search_results.length > 0
    },
  },
  computed: {
    searchIcon: function () {
      var results = this.haveSearchResults()

      return {
        'fa-search': !results,
        'fa-times': results,
      }
    }
  },
})
