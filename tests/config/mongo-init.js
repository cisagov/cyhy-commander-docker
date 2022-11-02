db.createUser({
  user: "cyhy",
  pwd: "cyhy",
  roles: [
    {
      role: "readWrite",
      db: "test_cyhy",
    },
  ],
});
