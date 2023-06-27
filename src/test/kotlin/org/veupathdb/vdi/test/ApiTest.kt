package org.veupathdb.vdi.test

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory
import com.fasterxml.jackson.module.kotlin.KotlinModule
import com.fasterxml.jackson.module.kotlin.readValue
import io.restassured.RestAssured
import io.restassured.RestAssured.given
import io.restassured.http.ContentType
import org.apache.logging.log4j.kotlin.logger
import org.awaitility.Awaitility.await
import org.awaitility.core.ConditionTimeoutException
import org.junit.jupiter.api.AfterAll
import org.junit.jupiter.api.BeforeAll
import org.junit.jupiter.api.TestInstance
import org.junit.jupiter.params.ParameterizedTest
import org.junit.jupiter.params.provider.MethodSource
import java.net.URL
import java.nio.file.Path
import java.time.Duration
import java.util.stream.Stream
import kotlin.io.path.name

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class ApiTest {
    private val AuthToken: String = System.getProperty("AUTH_TOKEN")
    private val AuthTokenKey: String = "Auth-Key"
    private val YamlMapper = ObjectMapper(YAMLFactory()).registerModule(KotlinModule.Builder().build())
    private val JsonMapper = ObjectMapper().registerModule(KotlinModule.Builder().build())

    // Files in the testdata resource directory must follow structure testdata/{dataset-type}/{upload-file}
    private val TestFilesDir = "testdata"

    // Keep track of all datasets created to clean them after all tests are done.
    private val DatasetsToClean = mutableListOf<String>()

    @BeforeAll
    internal fun setup() {
        RestAssured.baseURI = System.getProperty("BASE_URL")
    }

    @AfterAll
    internal fun teardown() {
        DatasetsToClean.forEach {
            logger().info("Cleaning dataset $it")
            given()
                .header(AuthTokenKey, AuthToken)
                .`when`()
                .delete("vdi-datasets/$it")
                .then()
                .statusCode(204)
        }
    }

    @ParameterizedTest
    @MethodSource("yamlTestCaseProvider")
    fun parameterizedTest(input: TestCase) {
        val path = Path.of(input.path)
        val meta: Map<String, Any> = mapOf(
            "datasetType" to mapOf(
                "name" to input.type,
                "version" to "1.0"
            ),
            "name" to path.name,
            "summary" to "Integration test case for file ${input.path}",
            "projects" to listOf(input.project),
            "dependencies" to emptyList<String>()
        )

        logger().info("Sending meta ${JsonMapper.writeValueAsString(meta)}")
        val datasetID = given() // Setup request
            .contentType(ContentType.MULTIPART)
            .header(AuthTokenKey, AuthToken)
            .multiPart("file", path.toFile())
            .multiPart("meta", JsonMapper.writeValueAsString(meta))
            // Execute request
            .`when`()
            .post("vdi-datasets")
            // Validate request and extract ID
            .then()
            .statusCode(200)
            .extract()
            .path<String>("datasetID")
        DatasetsToClean.add(datasetID)
        logger().info("Issued datasetID: $datasetID")

        awaitImportStatus(datasetID, if (input.expectation == Expectation.FAILED_IMPORT) "invalid" else "complete")

        if (input.expectation != Expectation.FAILED_IMPORT)
            awaitInstallStatus(datasetID, if (input.expectation == Expectation.FAILED_INSTALL) "failed-installation" else "complete")
    }

    /**
     * Provide test cases from YAML file.
     */
    private fun yamlTestCaseProvider(): Stream<TestCase> {
        val loader = Thread.currentThread().contextClassLoader
        val url: URL = loader.getResource(TestFilesDir)!!
        val testDataDir: String = url.path
        val testConfig = Path.of(testDataDir, "tests.yaml")
        val testSuite: TestSuite = YamlMapper.readValue(testConfig.toFile())
        return testSuite.tests.stream()
            .map {
                TestCase(
                    path = Path.of(testDataDir, it.path).toString(), // Construct path relative to testdata directory
                    expectation = it.expectation,
                    project = it.project,
                    type = it.type
                )
            }
    }

    private fun awaitInstallStatus(datasetID: String, status: String) {
        try {
            await()
                .atMost(Duration.ofSeconds(30L))
                .until {
                    getInstallStatus(datasetID) == status
                }
        } catch (e: ConditionTimeoutException) {
            throw AssertionError(
                "Test failed while waiting for inst all status of $datasetID to become \"complete\". " +
                        "Current status: ${getInstallStatus(datasetID)})", e
            )
        }
    }

    private fun awaitImportStatus(datasetID: String, status: String) {
        try {
            await()
                .pollInterval(Duration.ofSeconds(1L))
                .atMost(Duration.ofSeconds(30L))
                .until {
                    getImportStatus(datasetID) == status
                }
        } catch (e: ConditionTimeoutException) {
            throw AssertionError(
                "Test failed while waiting for import status of $datasetID to become \"complete\". " +
                        "Current status: ${getImportStatus(datasetID)})", e
            )
        }
    }

    private fun getImportStatus(datasetID: String): String {
        return given()
            .header(AuthTokenKey, AuthToken)
            .get("vdi-datasets/$datasetID")
            .then()
            .statusCode(200)
            .extract()
            .path("status.import")
    }

    private fun getInstallStatus(datasetID: String): String? {
        val node: Map<String, String> = given()
            .header(AuthTokenKey, AuthToken)
            .get("vdi-datasets/$datasetID")
            .then()
            .statusCode(200)
            .extract()
            .path("status.install[0]")
        return node["dataStatus"]
    }
}