import axios from 'axios'

const baseURL = process.env.REACT_APP_API_URL || ''

export default {
    getDetectorStatus: () => axios.get(`${baseURL}/health`),
    getDashboardData: () => axios.get(`${baseURL}/data`),
}
