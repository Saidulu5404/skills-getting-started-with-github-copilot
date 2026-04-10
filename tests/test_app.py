import pytest


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities_returns_success(self, client):
        # Arrange
        expected_activities = ["Chess Club", "Programming Class", "Gym Class"]

        # Act
        response = client.get("/activities")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        for activity_name in expected_activities:
            assert activity_name in data

    def test_get_activities_includes_all_details(self, client):
        # Arrange - chess club should have specific structure
        expected_keys = {"description", "schedule", "max_participants", "participants"}

        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        chess_club = activities["Chess Club"]
        assert all(key in chess_club for key in expected_keys)
        assert chess_club["max_participants"] == 12
        assert len(chess_club["participants"]) == 2

    def test_get_activities_shows_current_participants(self, client):
        # Arrange
        chess_club_expected_participants = ["michael@mergington.edu", "daniel@mergington.edu"]

        # Act
        response = client.get("/activities")
        activities = response.json()

        # Assert
        assert activities["Chess Club"]["participants"] == chess_club_expected_participants


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_user_succeeds(self, client):
        # Arrange
        activity_name = "Chess Club"
        new_email = "alex@mergington.edu"
        initial_participant_count = 2

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Signed up {new_email} for {activity_name}"
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activity = activities_response.json()[activity_name]
        assert len(activity["participants"]) == initial_participant_count + 1
        assert new_email in activity["participants"]

    def test_signup_duplicate_user_fails(self, client):
        # Arrange
        activity_name = "Chess Club"
        existing_email = "michael@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": existing_email}
        )

        # Assert
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_nonexistent_activity_fails(self, client):
        # Arrange
        invalid_activity = "Nonexistent Club"
        email = "student@mergington.edu"

        # Act
        response = client.post(
            f"/activities/{invalid_activity}/signup",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_multiple_users_to_same_activity(self, client):
        # Arrange
        activity_name = "Gym Class"
        users = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]

        # Act
        for email in users:
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200

        # Assert
        activities_response = client.get("/activities")
        activity = activities_response.json()[activity_name]
        assert len(activity["participants"]) == 5  # 2 initial + 3 new
        for email in users:
            assert email in activity["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_user_succeeds(self, client):
        # Arrange
        activity_name = "Chess Club"
        email_to_remove = "michael@mergington.edu"
        initial_count = 2

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email_to_remove}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email_to_remove} from {activity_name}"
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activity = activities_response.json()[activity_name]
        assert len(activity["participants"]) == initial_count - 1
        assert email_to_remove not in activity["participants"]

    def test_unregister_nonexistent_activity_fails(self, client):
        # Arrange
        invalid_activity = "Fake Club"
        email = "student@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{invalid_activity}/unregister",
            params={"email": email}
        )

        # Assert
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_user_not_in_activity_fails(self, client):
        # Arrange
        activity_name = "Chess Club"
        email_not_registered = "notregistered@mergington.edu"

        # Act
        response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email_not_registered}
        )

        # Assert
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]

    def test_unregister_then_can_signup_again(self, client):
        # Arrange
        activity_name = "Programming Class"
        email = "testuser@mergington.edu"

        # Act - signup first time
        signup_response1 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert - first signup succeeds
        assert signup_response1.status_code == 200

        # Act - unregister
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": email}
        )

        # Assert - unregister succeeds
        assert unregister_response.status_code == 200

        # Act - signup again
        signup_response2 = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": email}
        )

        # Assert - second signup succeeds
        assert signup_response2.status_code == 200
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity_name]["participants"]


class TestIntegrationFlows:
    """Integration tests for complete workflows"""

    def test_signup_verify_list_delete_verify_flow(self, client):
        # Arrange
        activity_name = "Chess Club"
        new_email = "integration@mergington.edu"

        # Act - signup
        signup_response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": new_email}
        )

        # Assert - signup success
        assert signup_response.status_code == 200

        # Act - verify in activity list
        get_response = client.get("/activities")
        activity = get_response.json()[activity_name]

        # Assert - visible in list
        assert new_email in activity["participants"]
        initial_count = len(activity["participants"])

        # Act - unregister
        delete_response = client.delete(
            f"/activities/{activity_name}/unregister",
            params={"email": new_email}
        )

        # Assert - delete success
        assert delete_response.status_code == 200

        # Act - verify removed from list
        final_response = client.get("/activities")
        final_activity = final_response.json()[activity_name]

        # Assert - no longer in list
        assert new_email not in final_activity["participants"]
        assert len(final_activity["participants"]) == initial_count - 1

    def test_multiple_operations_maintain_consistency(self, client):
        # Arrange
        activity = "Gym Class"
        users = ["user1@mergington.edu", "user2@mergington.edu", "user3@mergington.edu"]

        # Act - add multiple users
        for email in users:
            client.post(f"/activities/{activity}/signup", params={"email": email})

        # Assert - all added
        response = client.get("/activities")
        activity_data = response.json()[activity]
        initial_count = len(activity_data["participants"])
        assert initial_count == 5  # 2 original + 3 new

        # Act - remove middle user
        client.delete(f"/activities/{activity}/unregister", params={"email": users[1]})

        # Assert - count decreased
        response = client.get("/activities")
        activity_data = response.json()[activity]
        assert len(activity_data["participants"]) == initial_count - 1
        assert users[1] not in activity_data["participants"]
        assert users[0] in activity_data["participants"]
        assert users[2] in activity_data["participants"]
