# CertFlow Postman Testing Guide

This guide will walk you through testing the complete lifecycle of the CertFlow API using Postman. 

## 1. Prerequisites
1. Ensure the CertFlow API, PostgreSQL, Redis, and the Celery worker are running (e.g., using `docker compose up`).
2. Ensure you have your `API_KEY` handy from your `.env` file.
3. Download and install [Postman](https://www.postman.com/downloads/).

## 2. Set Up Your Postman Environment

To make testing easier, let's create environment variables so you don't have to copy-paste IDs manually.

1. Open Postman and click on **Environments** in the left sidebar.
2. Click the **+** (New) button to create a new environment. Name it "CertFlow Local".
3. Add the following variables:
   - `BASE_URL`: `http://localhost:8000`
   - `API_KEY`: *(paste your API key here)*
   - `JOB_ID`: *(leave blank for now)*
   - `CERTIFICATE_ID`: *(leave blank for now)*
4. Click **Save** and make sure "CertFlow Local" is selected in the environment dropdown in the top right corner of Postman.

---

## 3. Configure Global Authorization

Instead of adding the API key to every request, we can set it at the collection level.

1. Create a new Collection named **CertFlow API**.
2. Click on the collection name, go to the **Authorization** tab.
3. Select **API Key** from the Type dropdown.
4. Set the **Key** field to: `X-API-Key`
5. Set the **Value** field to: `{{API_KEY}}`
6. Set **Add to** to: `Header`
7. Click **Save**.

Now, every request inside this collection will automatically authenticate!

*(Note: Health checks don't require this, but it doesn't hurt if the header is present).*

---

## 4. Step-by-Step API Testing Flow

Create the following requests inside your "CertFlow API" collection.

### Step 1: Health Check (Liveness)
*Verifies the FastAPI server is running.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/health`
- **Click Send**.
- **Expected Response (200 OK)**:
  ```json
  {
    "status": "healthy"
  }
  ```

### Step 2: Readiness Check
*Verifies the API can connect to the Database.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/health/ready`
- **Click Send**.
- **Expected Response (200 OK)**:
  ```json
  {
    "status": "ready",
    "database": "ok",
    "redis": "ok"
  }
  ```

### Step 3: Create a Bulk Generation Job
*Submits a batch of recipients to generate certificates for.*

- **Method**: `POST`
- **URL**: `{{BASE_URL}}/api/v1/jobs`
- **Headers**:
  - `Idempotency-Key`: `postman-test-001` *(Optional, but good practice)*
- **Body** (select `raw` and `JSON`):
  ```json
  {
    "event": {
      "name": "Postman API Masterclass",
      "organization": "Developer Tools Inc.",
      "date": "2026-10-15"
    },
    "recipients": [
      {"name": "Alice Smith", "email": "alice@example.com"},
      {"name": "Bob Jones", "email": "bob@example.com"},
      {"name": "Charlie Brown", "email": "charlie@example.com"}
    ]
  }
  ```
- **Post-response script (Optional but highly recommended)**: Go to the "Tests" tab of this request and add this code to automatically save the job ID:
  ```javascript
  var jsonData = pm.response.json();
  pm.environment.set("JOB_ID", jsonData.id);
  ```
- **Click Send**.
- **Expected Response (202 Accepted)**: You will receive a job summary showing it is `QUEUED`.

### Step 4: Check Job Progress
*Since the job is processed in the background, we need to check its progress.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/api/v1/jobs/{{JOB_ID}}/progress`
- **Click Send** (you might want to hit send a few times to watch the numbers go up).
- **Expected Response (200 OK)**:
  ```json
  {
    "job_id": "...",
    "status": "PROCESSING",
    "total_count": 3,
    "success_count": 1,
    "failed_count": 0,
    "pending_count": 2,
    "processing_count": 0,
    "progress_percentage": 33.33
  }
  ```
  *Wait until `status` becomes `COMPLETED`.*

### Step 5: Get Full Job Details
*Retrieves all metadata about the job once completed.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/api/v1/jobs/{{JOB_ID}}`
- **Click Send**.
- **Expected Response (200 OK)**: Similar to the progress endpoint but includes the event details originally submitted.

### Step 6: List Recipients and Results
*Lists all recipients for the job to find the generated Certificate IDs.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/api/v1/jobs/{{JOB_ID}}/recipients?skip=0&limit=10`
- **Click Send**.
- **Expected Response (200 OK)**:
  ```json
  [
    {
      "id": "...",
      "name": "Alice Smith",
      "email": "alice@example.com",
      "status": "SUCCESS",
      "certificate_id": "uuid-for-alices-certificate",
      "error_message": null
    },
    // ...
  ]
  ```
- **Action**: Copy the `certificate_id` for one of the successful recipients and paste it into your `CERTIFICATE_ID` environment variable.

### Step 7: Download the PDF Certificate
*Downloads the actual generated PDF file.*

- **Method**: `GET`
- **URL**: `{{BASE_URL}}/api/v1/certificates/{{CERTIFICATE_ID}}/download`
- **Click Send**.
- **Postman Note**: The response will look like random gibberish text in the Postman body viewer because it is raw PDF binary data.
- **To View/Save**: Instead of clicking the standard blue "Send" button, click the dropdown arrow next to "Send" and choose **"Send and Download"**. This will execute the request and prompt you to save the generated PDF to your computer!

---

## 5. Testing Idempotency (Advanced)

CertFlow prevents accidentally creating duplicate jobs if you click send twice. You can test this:

1. Go back to your **Create a Bulk Generation Job** (`POST`) request.
2. Without changing the `Idempotency-Key` header (`postman-test-001`), click **Send** again.
3. Notice that the API returns `200 OK` (instead of `202 Accepted`) and returns the exact same `JOB_ID` that was already created, proving no duplicate was queued!
4. Change the `Idempotency-Key` to `postman-test-002` and click **Send**. You will now get a `202 Accepted` with a brand new `JOB_ID`.
