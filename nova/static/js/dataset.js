Vue.component('confirmdeletion', {
  template: '#modal-template',
  props: ['show']
})

var meta = new Vue ({
  el:'#meta-info',
  data: {
    token: readCookie('token'),
    bookmarked: false,
  },
  created: function() {
    var user_id = this.token.split('.')[0]
    var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id
    var headers = {
      'Auth-Token': this.token
    }

    this.$http.get(api_str, {headers: headers}).then((response) => {
      this.bookmarked = response.body.exists
    })
  },
  methods: {
    bookmark: function (event) {
      var headers = {
        'Auth-Token': this.token
      }

      var user_id = this.token.split('.')[0]
      var api_str = '/api/user/' + user_id + '/bookmarks/' + dataset_id

      if (this.bookmarked) {
        this.$http.delete(api_str, {headers: headers}).then((response) => {
          this.bookmarked = response.status != 200
        })
      }
      else {
        this.$http.post(api_str, null, {headers: headers}).then((response) => {
          this.bookmarked = response.status == 200
        })
      }
    }
  }
})

var description = new Vue ({
  el:'#dataset-description',
  data: {
    token: readCookie('token'),
    text: '',
    old: '',
    empty: true,
    editing: false,
  },
  created: function() {
    var options = {headers: { 'Auth-Token': this.token }}

    this.$http.get('/api/datasets/' + dataset_id, options).then((response) => {
      this.empty = response.body.description == null

      if (this.empty)
        this.text = "No description provided."
      else
        this.text = response.body.description
    })
  },
  methods: {
    onEdit: function () {
      this.editing = true
      this.old = this.text

      if (this.empty) {
        this.text = ''
      }
    },
    onSave: function () {
      this.editing = false
      this.empty = this.text == ''

      if (!this.empty) {
        var options = {headers: { 'Auth-Token': this.token }}

        this.$http.patch('/api/datasets/' + dataset_id, {description: this.text}, options).then((response) => {
          console.log("success")
        })
      }
    },
    onCancel: function () {
      this.editing = false
      this.text = this.old
    },
  },
  computed: {
    displayText: function () {
      return this.empty ? "No description provided." : this.text
    },
    buttonText: function () {
      return this.editing ? "Save" : "Edit"
    }
  }
})

var reviews = new Vue ({
  el:'#reviews',
  data: {
    token: readCookie('token'),
    average_rating: 0,
    base_rating: 0,
    half_star: false,
    reviews: [],
    review_count: 0,
    show_review_input: true,
    is_rated: false,
    rating_notified: false,
    review_text: '',
    n: 0,
    review_being_updated: false,
    review_under_updation: '',
    show_modal_delete_review: false
  },
  created: function() {
    var headers = {
      'Auth-Token': this.token
    }
    this.loadReviews(headers)
  },
  methods: {
    loadReviews: function (headers) {
      api_str = '/api/datasets/'+dataset_id+'/reviews'
      this.$http.get(api_str, {headers: headers}).then((response) => {
        this.review_count = parseInt(response.body.count)
        this.average_rating = response.body.avg_rating
        this.base_rating = Math.floor(this.average_rating)
        this.half_star = this.average_rating - this.base_rating >= .5

        if (response.body.count > 0) { 
          this.reviews = response.body.data
          this.show_review_input = ! response.body.self_reviewed
        }
      })
    },
    rate: function(n) { 
      this.n = n
      this.is_rated = true
      this.rating_notified = false
    },
    putReview: function(comment, rating) {
      var headers = {
        'Auth-Token': this.token
      }
      var jsonBody = {
        'comment': comment,
        'rating': rating
      }
      var user_id = this.token.split('.')[0]
      var api_str = '/api/datasets/'+dataset_id+'/reviews/'+user_id
      this.$http.put(api_str, jsonBody, {headers: headers}).then((response) => {
        this.loadReviews(headers)
      })
    },
    beginUpdatingReview: function(review) {
      this.n = review.rating
      this.review_text = review.comment
      this.review_under_updation = review.id
      this.review_being_updated = true
    },
    endUpdatingReview: function() {
      this.review_being_updated = false
    },
    sendUpdatedReview: function() {
      this.review_being_updated = false
      this.putReview(this.review_text, this.n)
    },
    sendNewReview: function() {
      if (this.is_rated && this.n > 0)
        this.putReview(this.review_text, this.n)
      else this.rating_notified = true
    },
    beginDeletingReview: function(review) {
      this.review_under_updation = review
      this.show_modal_delete_review = true
    },
    deleteReview: function() {
      this.review_text = ''
      this.n = 0
      this.is_rated = false
      var headers = {
        'Auth-Token': this.token
      }
      var api_str = '/api/datasets/'+this.review_under_updation.dataset_id+'/reviews/'+this.review_under_updation.user_id
      this.$http.delete(api_str, {headers: headers}).then((response) => {
        this.show_modal_delete_review = response.status != 200
      })
      this.loadReviews(headers)
    }, 
    dismissModal: function () {
      this.show_modal_delete_review = false
    },
    timeSince: function(date) {
      date = new Date(date)
      current = new Date()
      delta = current.getTimezoneOffset()
      seconds = Math.floor((new Date() - date) / 1000) + delta*60
      interval = Math.floor(seconds / 86400)
      if (interval >= 1) {
        return date.toLocaleString()
      }
      interval = Math.floor(seconds / 3600)
      if (interval >= 1) {
        return interval + " h ago"
      }
      interval = Math.floor(seconds / 60)
      if (interval >= 1) {
        return interval + " m ago"
      }
      return Math.floor(seconds) + " s ago"
    }
  }
})
